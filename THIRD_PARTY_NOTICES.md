# Third Party Notices

This file is the notice inventory for future portable zip / GUI distribution.

Current status: **pre-distribution inventory**. Final license verification is deferred until the actual packaged files, wheels, native libraries, and model files are fixed.

## Notice entry template

```text
Component:
Version:
Purpose:
License:
Copyright / Authors:
Source URL:
License text location:
Distribution note:
Status: confirmed / pending
```

## Project license

```text
Component: mojiokoshi
Version: 0.1.0
Purpose: local transcription tool
License: MIT
Copyright / Authors: karine-mue
Source URL: repository root
License text location: LICENSE
Distribution note: project code
Status: confirmed
```

## Python runtime and packaging

```text
Component: Python / CPython runtime
Version: pending
Purpose: runtime included by PyInstaller builds, if PyInstaller is used
License: PSF License, pending package audit
Copyright / Authors: Python Software Foundation
Source URL: https://www.python.org/
License text location: pending
Distribution note: needed only if the packaged application includes CPython runtime
Status: pending
```

```text
Component: PyInstaller
Version: pending
Purpose: Windows portable onedir packaging, if adopted
License: pending package audit
Copyright / Authors: PyInstaller contributors
Source URL: https://pyinstaller.org/
License text location: pending
Distribution note: packaging tool; include notices if its runtime / bootloader is distributed
Status: pending
```

## Python packages from requirements.txt

The versions below mirror `requirements.txt` at the time this file was created. Licenses must be verified from package metadata and upstream source before a portable zip is published.

```text
Component: faster-whisper
Version: 1.2.1
Purpose: Whisper transcription wrapper
License: pending package audit
Copyright / Authors: SYSTRAN / contributors, pending verification
Source URL: https://github.com/SYSTRAN/faster-whisper
License text location: pending
Distribution note: core runtime dependency
Status: pending
```

```text
Component: CTranslate2
Version: 4.8.1
Purpose: inference backend used by faster-whisper
License: pending package audit
Copyright / Authors: OpenNMT / contributors, pending verification
Source URL: https://github.com/OpenNMT/CTranslate2
License text location: pending
Distribution note: core runtime dependency; see native library audit section below
Status: pending
```

```text
Component: PyAV
Version: 18.0.0
Purpose: audio decoding dependency
License: pending package audit
Copyright / Authors: PyAV contributors, pending verification
Source URL: https://github.com/PyAV-Org/PyAV
License text location: pending
Distribution note: may include or load FFmpeg-related native binaries; see FFmpeg audit section below
Status: pending
```

```text
Component: FFmpeg
Version: pending
Purpose: media codec libraries used through PyAV, if bundled
License: pending build audit
Copyright / Authors: FFmpeg project, pending verification
Source URL: https://ffmpeg.org/
License text location: pending
Distribution note: confirm whether bundled binaries are LGPL or GPL builds before publication
Status: pending
```

```text
Component: tokenizers
Version: 0.23.1
Purpose: tokenizer dependency
License: pending package audit
Copyright / Authors: Hugging Face / contributors, pending verification
Source URL: https://github.com/huggingface/tokenizers
License text location: pending
Distribution note: runtime dependency
Status: pending
```

```text
Component: huggingface_hub
Version: 1.22.0
Purpose: model download / hub interaction dependency
License: pending package audit
Copyright / Authors: Hugging Face / contributors, pending verification
Source URL: https://github.com/huggingface/huggingface_hub
License text location: pending
Distribution note: runtime dependency when models are downloaded from Hugging Face
Status: pending
```

```text
Component: numpy
Version: 2.5.0
Purpose: numerical dependency
License: pending package audit
Copyright / Authors: NumPy contributors, pending verification
Source URL: https://numpy.org/
License text location: pending
Distribution note: runtime dependency
Status: pending
```

```text
Component: tqdm
Version: 4.68.3
Purpose: progress display dependency
License: pending package audit
Copyright / Authors: tqdm contributors, pending verification
Source URL: https://github.com/tqdm/tqdm
License text location: pending
Distribution note: runtime dependency
Status: pending
```

```text
Component: onnxruntime
Version: 1.27.0
Purpose: optional VAD / model runtime dependency path
License: pending package audit
Copyright / Authors: Microsoft / contributors, pending verification
Source URL: https://onnxruntime.ai/
License text location: pending
Distribution note: runtime dependency from faster-whisper dependency set
Status: pending
```

```text
Component: Silero VAD model
Version: pending
Purpose: VAD model used when `vad_filter = true`
License: pending model audit
Copyright / Authors: Silero / contributors, pending verification
Source URL: pending
License text location: pending
Distribution note: confirm model file source and license before bundling
Status: pending
```

## CTranslate2 native library audit

CTranslate2 wheels may include native libraries. The actual files in the portable zip must be identified from the final build output.

```text
Component: Intel MKL
Version: pending
Purpose: native math backend, if bundled by CTranslate2 wheel
License: pending native library audit
Copyright / Authors: Intel, pending verification
Source URL: pending
License text location: pending
Distribution note: confirm whether this library is present in the final package and include required license text if present
Status: pending
```

```text
Component: oneDNN
Version: pending
Purpose: native acceleration backend, if bundled by CTranslate2 wheel
License: pending native library audit
Copyright / Authors: oneDNN contributors, pending verification
Source URL: pending
License text location: pending
Distribution note: confirm whether this library is present in the final package
Status: pending
```

```text
Component: OpenBLAS
Version: pending
Purpose: native math backend, if bundled by CTranslate2 wheel
License: pending native library audit
Copyright / Authors: OpenBLAS contributors, pending verification
Source URL: pending
License text location: pending
Distribution note: confirm whether this library is present in the final package
Status: pending
```

Additional `.dll`, `.so`, or `.dylib` files found in the CTranslate2 wheel or final package must be added here before publication.

## Whisper / model files

```text
Component: OpenAI Whisper / Whisper model weights
Version: pending
Purpose: transcription model files
License: pending model audit
Copyright / Authors: OpenAI / contributors, pending verification
Source URL: https://github.com/openai/whisper
License text location: pending
Distribution note: model files are not included in the initial app zip; if model pack zip is created, include model notices there as well
Status: pending
```

## CUDA / NVIDIA libraries

Initial portable zip builds do not include CUDA, cuDNN, cuBLAS, or NVIDIA pip package DLLs.

```text
Component: NVIDIA CUDA / cuDNN / cuBLAS libraries
Version: not bundled in initial portable zip
Purpose: optional GPU acceleration
License: out of initial distribution scope
Copyright / Authors: NVIDIA, pending verification if ever bundled
Source URL: pending
License text location: pending
Distribution note: users who need CUDA are expected to prepare their own environment until a separate CUDA packaging issue verifies redistribution terms
Status: not bundled
```

## GUI framework

No GUI framework is selected yet. Add the selected framework here before GUI distribution.
