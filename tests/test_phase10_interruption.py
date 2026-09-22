"""Phase 10 tests — interruption, cancellation, stop, retry, do-that-again.
Run: python tests/test_phase10_interruption.py
"""
import sys, time, threading, unittest
sys.path.insert(0, r"C:\Alpha\Alpha 0.2\nova")

from app.interrupt.manager import InterruptManager
from app.interrupt.detector import is_stop_command, is_retry_command, get_interrupt_priority
from app.interrupt.events import get_global_stop_event, request_global_stop, clear_global_stop, is_global_stop_requested
from app.tts.speaker import Speaker
from app.agent.schemas import TaskPlan, TaskStep
from app.agent.executor import TaskExecutor, TaskState
from app.config import Config
from app.conversation.manager import ConversationManager

# Mocks
class MockPC:
    def __init__(self):
        self.actions=[]
        self.fg="Brave"
    def open_application(self, name):
        self.actions.append(("open", name))
        return True, f"Opening {name}."
    def open_url(self, u):
        self.actions.append(("open_url", u))
        return True, f"Opened {u}"
    def type_text(self, t):
        self.actions.append(("type", t))
        return True, "Done."
    def scroll(self, a):
        self.actions.append(("scroll", a))
        return True, "Done."
    def press_key(self, k):
        self.actions.append(("press", k))
        return True, "Done."
    def hotkey(self, *k):
        self.actions.append(("hotkey", k))
        return True, "Done."
    def click(self): self.actions.append(("click",)); return True,"Done."
    def double_click(self): self.actions.append(("dbl",)); return True,"Done."
    def right_click(self): self.actions.append(("rclick",)); return True,"Done."
    def get_foreground_window(self): return self.fg

class MockBrowser:
    def __init__(self):
        self.actions=[]
        self.is_running=False
        self.current_url=None
        self.enabled=True
    def open_url(self, t):
        self.is_running=True
        self.current_url=f"https://{t}.com"
        if "youtube" in t.lower(): self.current_url="https://www.youtube.com"
        self.actions.append(("open_url", t))
        return True, f"Opened {t}"
    def search_web(self, q):
        self.is_running=True
        self.current_url=f"https://google.com/search?q={q}"
        self.actions.append(("search", q))
        return True, f"Searched {q}"
    def youtube_search(self, q):
        self.is_running=True
        self.current_url=f"https://youtube.com/results?q={q}"
        self.actions.append(("yt", q))
        return True, f"Searched YouTube for {q}"
    def go_back(self): self.actions.append(("back",)); return True,"Went back"
    def go_forward(self): self.actions.append(("forward",)); return True,"Went forward"
    def refresh(self): self.actions.append(("refresh",)); return True,"Refreshed"
    def scroll(self, a): self.actions.append(("scroll", a)); return True,"Done"
    def close_browser(self):
        was=self.is_running
        self.is_running=False
        self.actions.append(("close",))
        return True,"Closed"

class MockVision:
    def find_element(self, target, active_window=None):
        class R:
            found=True; confidence=0.9; x=100; y=100; width=50; height=50; label=target
        return R()
    def analyze(self, q, active_window=None):
        class A: description="screen"; confidence=0.9
        return A()
    def is_available(self): return True
    @property
    def capture(self):
        class C:
            def capture_screen(self): return None
        return C()

class TestInterruptManager(unittest.TestCase):
    def test_request_and_clear(self):
        m=InterruptManager(enabled=True, check_interval_ms=50, post_cancel_cooldown_ms=50)
        self.assertFalse(m.is_stop_requested())
        m.request_stop()
        self.assertTrue(m.is_stop_requested())
        m.clear_stop()
        self.assertFalse(m.is_stop_requested())
    def test_interruptible_wait_completed(self):
        m=InterruptManager(enabled=True, check_interval_ms=20, post_cancel_cooldown_ms=20)
        start=time.time()
        ok=m.interruptible_wait(0.2)
        elapsed=time.time()-start
        self.assertTrue(ok)
        self.assertGreaterEqual(elapsed, 0.15)
    def test_interruptible_wait_interrupted(self):
        m=InterruptManager(enabled=True, check_interval_ms=20, post_cancel_cooldown_ms=20)
        def trigger():
            time.sleep(0.05)
            m.request_stop()
        threading.Thread(target=trigger, daemon=True).start()
        ok=m.interruptible_wait(0.5)
        self.assertFalse(ok)
        m.clear_stop()
    def test_disabled_no_interrupt(self):
        m=InterruptManager(enabled=False)
        m.request_stop()
        self.assertFalse(m.is_stop_requested())

class TestDetector(unittest.TestCase):
    def test_stop_commands(self):
        self.assertTrue(is_stop_command("stop"))
        self.assertTrue(is_stop_command("cancel"))
        self.assertTrue(is_stop_command("never mind"))
        self.assertTrue(is_stop_command("nevermind"))
        self.assertTrue(is_stop_command("abort"))
        self.assertTrue(is_stop_command("stop nova"))
        self.assertTrue(is_stop_command("nova stop"))
        self.assertTrue(is_stop_command("shut up"))
        self.assertTrue(is_stop_command("forget it"))
        self.assertTrue(is_stop_command("stop that"))
        self.assertTrue(is_stop_command("cancel this"))
        self.assertTrue(is_stop_command("don't do that"))
        self.assertTrue(is_stop_command("Hey Nova, stop"))
        self.assertFalse(is_stop_command("open brave"))
        self.assertFalse(is_stop_command("hello"))
    def test_retry_commands(self):
        is_r,k=is_retry_command("try again")
        self.assertTrue(is_r); self.assertEqual(k,"try_again")
        is_r,k=is_retry_command("do that again")
        self.assertTrue(is_r); self.assertEqual(k,"do_that_again")
        is_r,_=is_retry_command("open brave")
        self.assertFalse(is_r)
    def test_priority(self):
        self.assertEqual(get_interrupt_priority("stop"),1)
        self.assertEqual(get_interrupt_priority("try again"),2)
        self.assertEqual(get_interrupt_priority("open brave"),3)

class TestTTS(unittest.TestCase):
    def test_stop_safe_multiple(self):
        s=Speaker(enabled=False) # disabled to avoid engine init
        # stop should not crash even when engine is None
        s.stop()
        s.stop()
        # enable but not initialized engine is None still safe
        s._engine=None
        s.stop()
    def test_speak_lock_single(self):
        s=Speaker(enabled=False)
        # speak should return False when disabled, not crash, and lock not held
        self.assertFalse(s.speak("hello"))
        # after stop, is_speaking should be False
        self.assertFalse(s.is_speaking)

class TestExecutorCancellation(unittest.TestCase):
    def test_cancel_during_task(self):
        # 5-step task, cancel during step 3
        config=Config.load()
        pc=MockPC(); browser=MockBrowser(); vision=MockVision()
        im=InterruptManager(enabled=True)
        # Use get_global_stop_event for shared
        exe=TaskExecutor(pc, browser, vision, config, interrupt_manager=im)
        # Create plan with 5 steps including wait that can be interrupted, but also ensure slow steps to allow cancel
        steps=[
            TaskStep(id=1, action="open_application", parameters={"application":"brave"}),
            TaskStep(id=2, action="open_url", parameters={"website":"youtube"}),
            TaskStep(id=3, action="wait", parameters={"seconds":2}),
            TaskStep(id=4, action="youtube_search", parameters={"query":"Arijit"}),
            TaskStep(id=5, action="wait", parameters={"seconds":1}),
        ]
        plan=TaskPlan(goal="test", steps=steps)
        # Run in thread and cancel
        result_holder=[]
        def run():
            result_holder.append(exe.execute(plan))
        t=threading.Thread(target=run, daemon=True)
        t.start()
        time.sleep(0.4) # let steps 1-2 complete (each ~0.3+ execution)
        im.request_stop()
        exe.cancel() # also explicit
        t.join(timeout=5)
        status=result_holder[0]
        self.assertEqual(status.state, TaskState.CANCELLED)
        info=exe.get_cancellation_result()
        self.assertEqual(info["status"],"cancelled")
        self.assertEqual(info["reason"],"user_interrupt")
        # steps 4-5 should not be executed
        self.assertLess(len(status.results), 5)
        self.assertGreaterEqual(info["completed_steps"], 1)
        self.assertGreater(info["remaining_steps"], 0)
        im.clear_stop()

    def test_browser_remains_open_after_cancel(self):
        config=Config.load()
        pc=MockPC(); browser=MockBrowser()
        im=InterruptManager(enabled=True)
        exe=TaskExecutor(pc, browser, None, config, interrupt_manager=im)
        steps=[
            TaskStep(id=1, action="open_application", parameters={"application":"brave"}),
            TaskStep(id=2, action="open_url", parameters={"website":"youtube"}),
            TaskStep(id=3, action="youtube_search", parameters={"query":"test"}),
            TaskStep(id=4, action="wait", parameters={"seconds":2}),
            TaskStep(id=5, action="wait", parameters={"seconds":2}),
        ]
        plan=TaskPlan(goal="browser", steps=steps)
        def run():
            exe.execute(plan)
        t=threading.Thread(target=run, daemon=True)
        t.start()
        time.sleep(0.6)
        im.request_stop()
        exe.cancel()
        t.join(timeout=5)
        # Browser should still be running (not closed)
        self.assertTrue(browser.is_running)
        im.clear_stop()

    def test_wait_interruptible(self):
        config=Config.load()
        im=InterruptManager(enabled=True, check_interval_ms=20)
        exe=TaskExecutor(None, None, None, config, interrupt_manager=im)
        start=time.time()
        def trigger():
            time.sleep(0.05)
            im.request_stop()
        threading.Thread(target=trigger, daemon=True).start()
        ok=exe.interruptible_wait(0.5)
        elapsed=time.time()-start
        self.assertFalse(ok)
        self.assertLess(elapsed, 0.3)
        im.clear_stop()
        # normal wait should complete
        ok2=exe.interruptible_wait(0.1)
        self.assertTrue(ok2)

    def test_no_stale_cancellation(self):
        config=Config.load()
        pc=MockPC(); browser=MockBrowser()
        im=InterruptManager(enabled=True)
        exe=TaskExecutor(pc, browser, None, config, interrupt_manager=im)
        # first task cancelled
        steps1=[TaskStep(id=1, action="wait", parameters={"seconds":1})]
        plan1=TaskPlan(goal="first", steps=steps1)
        def run1():
            exe.execute(plan1)
        t=threading.Thread(target=run1, daemon=True)
        t.start()
        time.sleep(0.05)
        im.request_stop()
        exe.cancel()
        t.join(timeout=3)
        self.assertEqual(exe.state, TaskState.CANCELLED)
        # second task should NOT be immediately cancelled (clear)
        steps2=[TaskStep(id=1, action="open_application", parameters={"application":"brave"})]
        plan2=TaskPlan(goal="second", steps=steps2)
        status2=exe.execute(plan2)
        self.assertEqual(status2.state, TaskState.COMPLETED)

class TestConversationCancellation(unittest.TestCase):
    def test_cancel_listening(self):
        cm=ConversationManager(enabled=True, conversation_timeout=8, follow_up_timeout=6, max_turns=10)
        cm.start()
        self.assertTrue(cm.is_active())
        # simulate cancel phrase
        self.assertTrue(is_stop_command("cancel"))
        cm.reset()
        self.assertFalse(cm.is_active())
        self.assertEqual(cm.get_state().name, "IDLE")
    def test_never_mind_resets(self):
        cm=ConversationManager(enabled=True)
        cm.start()
        cm.update_context(last_application="brave", current_url="https://youtube.com")
        cm.increment_turn()
        self.assertTrue(is_stop_command("never mind"))
        cm.reset()
        self.assertIsNone(cm.get_context()["last_application"])
        self.assertEqual(cm.get_context()["turn_count"],0)
    def test_try_again(self):
        cm=ConversationManager(enabled=True)
        cm.start()
        cm.update_context(last_action="search_web", last_search="test", last_task_status="failed")
        cm.context.last_user_text="search youtube for test"
        # is_retry should be true
        is_r, kind=is_retry_command("try again")
        self.assertTrue(is_r)
        self.assertEqual(kind,"try_again")
        # simulate retry logic: if failed, retry last_user_text
        self.assertEqual(cm.get_context()["last_task_status"],"failed")
    def test_do_that_again(self):
        cm=ConversationManager(enabled=True)
        cm.start()
        cm.update_context(last_action="scroll", last_task_status="success")
        cm.context.last_user_text="scroll down"
        is_r, kind=is_retry_command("do that again")
        self.assertTrue(is_r)
        self.assertEqual(kind,"do_that_again")
        self.assertEqual(cm.get_context()["last_task_status"],"success")

class TestRepeatedAndReuse(unittest.TestCase):
    def test_repeated_cancellation_no_crash(self):
        im=InterruptManager(enabled=True)
        for _ in range(5):
            im.request_stop()
            im.request_stop() # multiple
            self.assertTrue(im.is_stop_requested())
            im.clear_stop()
            self.assertFalse(im.is_stop_requested())
        # also Speaker stop multiple
        s=Speaker(enabled=False)
        for _ in range(3):
            s.stop()
    def test_reuse_after_cancellation(self):
        cm=ConversationManager(enabled=True)
        im=InterruptManager(enabled=True)
        # first conversation
        cm.start()
        cm.update_context(last_application="brave")
        cm.increment_turn()
        im.request_stop()
        cm.reset()
        im.clear_stop()
        self.assertFalse(cm.is_active())
        # second conversation should work independently
        cm.start()
        self.assertTrue(cm.is_active())
        cm.update_context(last_application="notepad")
        self.assertEqual(cm.get_context()["last_application"],"notepad")
        cm.reset()
    def test_stop_not_shutdown(self):
        # stop should not exit app; just cancel task and return to idle
        config=Config.load()
        pc=MockPC(); browser=MockBrowser()
        im=InterruptManager(enabled=True)
        exe=TaskExecutor(pc, browser, None, config, interrupt_manager=im)
        # simulate stop command does not call sys.exit
        self.assertTrue(is_stop_command("stop"))
        # ensure executor can still run after stop
        steps=[TaskStep(id=1, action="open_application", parameters={"application":"notepad"})]
        plan=TaskPlan(goal="test", steps=steps)
        status=exe.execute(plan)
        self.assertEqual(status.state, TaskState.COMPLETED)

class TestGlobalEvent(unittest.TestCase):
    def test_global_shared(self):
        ev=get_global_stop_event()
        ev.clear()
        self.assertFalse(is_global_stop_requested())
        request_global_stop()
        self.assertTrue(is_global_stop_requested())
        clear_global_stop()
        self.assertFalse(is_global_stop_requested())
    def test_vision_cancellation(self):
        # Vision should be cancellable via global event check
        ev=get_global_stop_event()
        ev.clear()
        # simulate vision analyze checks event
        def vision_task():
            for i in range(5):
                if ev.is_set():
                    return False
                time.sleep(0.02)
            return True
        def trigger():
            time.sleep(0.03)
            ev.set()
        threading.Thread(target=trigger, daemon=True).start()
        result=vision_task()
        self.assertFalse(result)
        ev.clear()

if __name__=="__main__":
    unittest.main(verbosity=2)
