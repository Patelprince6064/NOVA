"""Speech-to-text via faster-whisper.

The model is loaded once and reused. Audio is expected as a 1-D NumPy
float32 array at 16 kHz mono (or the configured sample rate).
All audio stays in memory and is released after transcription.
"""

import logging
import re
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


class Transcriber:
    """Reusable Whisper transcription engine."""

    def __init__(
        self,
        model_name: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
        language: Optional[str] = None,
    ) -> None:
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self._model = None  # lazy-loaded WhisperModel

    # ------------------------------------------------------------------
    # Model loading — called once at startup
    # ------------------------------------------------------------------
    def load(self) -> None:
        """Load the Whisper model (downloads on first run)."""
        if self._model is not None:
            logger.debug("Model already loaded, skipping.")
            return

        print("Loading speech recognition model...")
        print("This may take a little time on the first run.")
        logger.info(
            "Loading Whisper model: name=%s device=%s compute=%s",
            self.model_name,
            self.device,
            self.compute_type,
        )

        try:
            from faster_whisper import WhisperModel

            # faster-whisper will download the model automatically if missing
            self._model = WhisperModel(
                self.model_name,
                device=self.device,
                compute_type=self.compute_type,
            )
        except Exception as exc:
            logger.exception("Failed to load Whisper model")
            raise RuntimeError(
                f"Failed to load Whisper model '{self.model_name}' "
                f"on device '{self.device}' ({self.compute_type}): {exc}\n"
                "Troubleshooting:\n"
                "  - Check internet connection for first-time download.\n"
                "  - Verify WHISPER_DEVICE is 'cpu' or 'cuda'.\n"
                "  - Verify WHISPER_COMPUTE_TYPE (cpu: int8/float32, cuda: float16/int8_float16).\n"
                "  - Try WHISPER_MODEL=tiny for a smaller model."
            ) from exc

        print("Speech recognition ready.\n")
        logger.info("Whisper model loaded successfully.")

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    # ------------------------------------------------------------------
    # Transcription
    # ------------------------------------------------------------------
    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> str:
        """Transcribe mono float32 audio.

        Args:
            audio: 1-D float32 array, mono, at `sample_rate`.
            sample_rate: Sample rate of the audio (for logging only;
                         faster-whisper expects 16 kHz).

        Returns:
            Clean transcription text (may be empty string if no speech).

        Raises:
            RuntimeError: if model not loaded or transcription fails.
        """
        if self._model is None:
            raise RuntimeError("Model not loaded. Call load() first.")

        if audio is None or audio.size == 0:
            logger.info("Empty audio buffer — nothing to transcribe.")
            return ""

        # Ensure correct dtype
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        # Basic silence check: if RMS is extremely low, skip transcription
        # to avoid wasting time on pure silence.
        rms = float(np.sqrt(np.mean(audio**2))) if audio.size > 0 else 0.0
        if rms < 0.005:
            logger.info("Audio RMS very low (%.5f) — likely silence.", rms)
            # Still attempt transcription; Whisper will return empty anyway,
            # but we log it for diagnostics without blocking.
            pass

        logger.info(
            "Transcribing audio: samples=%d sr=%d duration=%.2fs rms=%.4f",
            audio.size,
            sample_rate,
            audio.size / sample_rate if sample_rate else 0,
            rms,
        )

        try:
            segments, info = self._model.transcribe(
                audio,
                language=self.language,
                beam_size=5,
                vad_filter=True,  # filter out silence segments
            )
            # faster-whisper returns a generator for segments
            text_parts = [seg.text for seg in segments]
            raw_text = " ".join(text_parts)
            cleaned = self._clean_text(raw_text)
            logger.info(
                "Transcription completed: detected_language=%s lang_prob=%.2f text_len=%d",
                getattr(info, "language", "?"),
                getattr(info, "language_probability", 0),
                len(cleaned),
            )
            # Do NOT log speech content by default for privacy
            logger.debug("Transcription raw: %r -> cleaned: %r", raw_text, cleaned)
            return cleaned
        except Exception as exc:
            logger.exception("Transcription failed")
            raise RuntimeError(f"Unable to transcribe audio: {exc}") from exc

    # ------------------------------------------------------------------
    @staticmethod
    def _clean_text(text: str) -> str:
        """Normalize whitespace and strip."""
        if not text:
            return ""
        # Collapse all whitespace to single spaces
        text = re.sub(r"\s+", " ", text).strip()
        return text
