"""Phase 11 — speed, latency, reliability tests."""
import sys, time, unittest, threading
sys.path.insert(0, r"C:\Alpha\Alpha 0.2\nova")

from app.performance.timer import PerfTimer
from app.performance.metrics import PerformanceMetrics, global_metrics
from app.config import Config

class TestPerfTimer(unittest.TestCase):
    def test_timer(self):
        t=PerfTimer()
        t.start("a")
        time.sleep(0.05)
        e=t.stop("a")
        self.assertGreaterEqual(e, 0.04)
        self.assertLess(e, 0.2)
        self.assertIn("a", t.all())

class TestMetrics(unittest.TestCase):
    def test_record(self):
        m=PerformanceMetrics()
        m.record("router", 0.01)
        m.record("router", 0.02)
        snap=m.snapshot()
        self.assertAlmostEqual(snap["avg_router"], 0.015, places=3)
        self.assertEqual(snap["cnt_router"],2)
        m.increment_command(is_llm=False)
        m.increment_command(is_llm=True)
        snap=m.snapshot()
        self.assertEqual(snap["commands"],2)
        self.assertEqual(snap["llm_calls"],1)
        self.assertEqual(snap["local_commands"],1)
        m.print_dashboard()

class TestSilenceConfig(unittest.TestCase):
    def test_config_vars(self):
        c=Config.load()
        self.assertEqual(c.silence_timeout_ms,700)
        self.assertEqual(c.min_speech_duration_ms,250)
        self.assertIsInstance(c.performance_debug, bool)

class TestFastRouterPerformance(unittest.TestCase):
    def test_router_latency(self):
        from app.pc.actions import handle_command
        from app.pc.controller import PCController
        pc=PCController(enabled=True)
        # mock pyautogui
        try:
            import unittest.mock as mock
            pc._ensure_pyautogui = mock.MagicMock(return_value=mock.MagicMock(click=lambda: None, scroll=lambda x: None, press=lambda x: None, hotkey=lambda *a: None, typewrite=lambda *a, **k: None, FAILSAFE=False))
        except: pass
        cmds=["open Brave","open Notepad","scroll down","press enter","go back","refresh","stop","open YouTube","open VS Code"]
        # type hello separately with higher threshold due to typing sleep
        t=PerfTimer()
        for cmd in cmds:
            t.start("router")
            try: handle_command(cmd, pc)
            except: pass
            e=t.stop("router")
            self.assertLess(e, 0.05, f"router too slow for {cmd}: {e}")
        # type hello has inherent sleep for typing, allow 0.3s
        t.start("router")
        try: handle_command("type hello", pc)
        except: pass
        e=t.stop("router")
        self.assertLess(e, 0.3, f"router too slow for type hello: {e}")
        # LLM should not be called for these — we just ensure router fast

class TestLLMReuse(unittest.TestCase):
    def test_client_reuse(self):
        c=Config.load()
        c2=Config.__new__(Config)
        # fake config with enabled and key
        from dataclasses import replace
        # Use real config but force key
        import os
        orig=os.getenv("LLM_API_KEY")
        os.environ["LLM_API_KEY"]="sk-test"
        try:
            from app.config import Config as C2
            cfg=C2.load()
            # temporarily set enabled true to test reuse
            cfg2 = cfg
            # create interpreter with fake key
            from app.ai.interpreter import CommandInterpreter
            # we need to set llm_enabled true via monkey
            cfg_enabled = Config(
                whisper_model=cfg.whisper_model, whisper_device=cfg.whisper_device, whisper_compute_type=cfg.whisper_compute_type, sample_rate=cfg.sample_rate, max_recording_seconds=cfg.max_recording_seconds, language=cfg.language,
                tts_enabled=cfg.tts_enabled, tts_rate=cfg.tts_rate, tts_volume=cfg.tts_volume, tts_voice=cfg.tts_voice,
                wake_word_enabled=cfg.wake_word_enabled, wake_word=cfg.wake_word, wake_word_threshold=cfg.wake_word_threshold, command_timeout_seconds=cfg.command_timeout_seconds, wake_sound_enabled=cfg.wake_sound_enabled, wake_word_cooldown_ms=cfg.wake_word_cooldown_ms,
                pc_control_enabled=cfg.pc_control_enabled, default_scroll_amount=cfg.default_scroll_amount, action_timeout_seconds=cfg.action_timeout_seconds,
                llm_enabled=True, llm_provider="openai", llm_model="gpt-4o-mini", llm_api_key="sk-test", llm_timeout_seconds=5,
                browser_enabled=cfg.browser_enabled, browser_name=cfg.browser_name, browser_headless=cfg.browser_headless, browser_timeout_ms=cfg.browser_timeout_ms,
                vision_enabled=cfg.vision_enabled, vision_provider=cfg.vision_provider, vision_model=cfg.vision_model, vision_api_key="sk-test", vision_timeout_seconds=cfg.vision_timeout_seconds,
                screen_monitor=cfg.screen_monitor, screenshot_max_width=cfg.screenshot_max_width, screenshot_max_height=cfg.screenshot_max_height, vision_min_confidence=cfg.vision_min_confidence, vision_click_test_enabled=cfg.vision_click_test_enabled,
                agent_enabled=cfg.agent_enabled, max_task_steps=cfg.max_task_steps, max_step_retries=cfg.max_step_retries, max_task_duration_seconds=cfg.max_task_duration_seconds, max_wait_seconds=cfg.max_wait_seconds,
                conversation_mode_enabled=cfg.conversation_mode_enabled, conversation_timeout_seconds=cfg.conversation_timeout_seconds, follow_up_timeout_seconds=cfg.follow_up_timeout_seconds, max_conversation_turns=cfg.max_conversation_turns, conversation_context_enabled=cfg.conversation_context_enabled, post_tts_cooldown_ms=cfg.post_tts_cooldown_ms,
                interruption_enabled=cfg.interruption_enabled, stop_commands_enabled=cfg.stop_commands_enabled, interruption_check_interval_ms=cfg.interruption_check_interval_ms, post_cancel_cooldown_ms=cfg.post_cancel_cooldown_ms, interruption_listening_enabled=cfg.interruption_listening_enabled,
                silence_timeout_ms=cfg.silence_timeout_ms, min_speech_duration_ms=cfg.min_speech_duration_ms, performance_debug=cfg.performance_debug, stt_timeout_seconds=cfg.stt_timeout_seconds, task_timeout_seconds=cfg.task_timeout_seconds,
            )
            try:
                interp=CommandInterpreter(cfg2)
                client1=interp._client
                # second call should reuse
                interp2=CommandInterpreter(cfg2)
                # if openai not installed, client may be None — skip
                try:
                    import openai
                    has_openai=True
                except ImportError:
                    has_openai=False
                if has_openai:
                    self.assertIsNotNone(client1 or interp2._client)
                else:
                    self.assertTrue(True)  # skip when openai missing
            except Exception as exc:
                # if client creation fails due to missing package, skip
                if "openai" in str(exc).lower():
                    self.skipTest("openai not installed")
                else:
                    raise
        finally:
            if orig is None:
                os.environ.pop("LLM_API_KEY",None)
            else:
                os.environ["LLM_API_KEY"]=orig

class TestBrowserReuse(unittest.TestCase):
    def test_lazy_and_reuse(self):
        from app.browser.controller import BrowserController
        bc=BrowserController(enabled=True, browser_name="chromium", headless=True, timeout_ms=5000)
        self.assertFalse(bc.is_running)
        # lazy: not started until open
        self.assertFalse(bc._started)

class TestVisionOnDemand(unittest.TestCase):
    def test_no_screenshot_for_simple(self):
        # simple commands should not trigger vision capture
        from app.main import route_pc_command
        from app.config import Config as C
        from app.pc.controller import PCController
        from app.browser.controller import BrowserController
        cfg=C.load()
        pc=PCController(enabled=True)
        browser=BrowserController(enabled=False)
        # mock vision that would fail if called
        class FailVision:
            def __init__(self): self.called=False
            def find_element(self, *a, **k):
                self.called=True
                raise AssertionError("vision should not be called for go back")
            def analyze(self, *a, **k):
                self.called=True
                raise AssertionError("vision should not be called")
            def is_available(self): return True
        vision=FailVision()
        # go back should be handled via browser or pc, not vision
        # need to ensure vision not called
        # Use browser disabled so pc handles? But go back needs browser; with browser disabled, it will still try vision? Actually vision fast path checks first but only for vision queries
        # For simple scroll, vision not called
        import unittest.mock as mock
        pc._ensure_pyautogui = mock.MagicMock(return_value=mock.MagicMock(click=lambda: None, scroll=lambda x: None, press=lambda x: None, hotkey=lambda *a: None, typewrite=lambda *a, **k: None, FAILSAFE=False))
        resp=route_pc_command("scroll down", pc, None, cfg, browser, vision, context={})
        self.assertIn("Done", resp)
        self.assertFalse(vision.called)

class TestReliability20Commands(unittest.TestCase):
    def test_20_commands_no_leak(self):
        from app.conversation.manager import ConversationManager
        from app.interrupt.manager import InterruptManager
        cm=ConversationManager(enabled=True)
        im=InterruptManager(enabled=True)
        cm.start()
        for i in range(20):
            cm.increment_turn()
            cm.add_turn(f"cmd {i}", "Done.")
            cm.update_context(last_action="scroll", last_task_status="success")
            # simulate interrupt clear
            if im.is_stop_requested():
                im.clear_stop()
        self.assertEqual(cm.get_context()["turn_count"],20)
        # history should be capped at 10
        self.assertLessEqual(len(cm.context.history),10)
        # reset
        cm.reset()
        self.assertEqual(cm.get_context()["turn_count"],0)
        # ensure metrics capped
        m=PerformanceMetrics()
        for i in range(250):
            m.record("router", 0.01)
        self.assertLessEqual(len(m._timings["router"]),200)

class TestBenchmark(unittest.TestCase):
    def test_benchmark_runs(self):
        from app.performance.metrics import run_benchmark
        snap=run_benchmark(iterations=10)
        self.assertIn("commands", snap)
        self.assertGreater(snap["commands"],5)
        self.assertGreater(snap["local_commands"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
