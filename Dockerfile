# Official image, explicit version; no PyMuPDF, LibreOffice, Poppler or LLM APIs.
FROM python:3.14.5-slim-trixie AS ocr-builder

RUN apt-get update \
    && apt-get install -y --no-install-recommends cmake g++ make pkg-config libpng-dev libjpeg62-turbo-dev zlib1g-dev curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /build
# Only JPEG/PNG are needed by OCR. Build Leptonica without distro TIFF/JBIG.
RUN curl --fail --location https://github.com/DanBloomberg/leptonica/archive/refs/tags/1.87.0.tar.gz -o leptonica.tar.gz \
    && tar -xzf leptonica.tar.gz \
    && cmake -S leptonica-1.87.0 -B lept-build -DCMAKE_BUILD_TYPE=Release \
       -DCMAKE_INSTALL_PREFIX=/opt/ocr -DCMAKE_INSTALL_LIBDIR=lib \
       -DBUILD_SHARED_LIBS=ON -DBUILD_PROG=OFF \
       -DENABLE_GIF=OFF -DENABLE_TIFF=OFF -DENABLE_WEBP=OFF \
       -DENABLE_OPENJPEG=OFF -DENABLE_JPEG=ON -DENABLE_PNG=ON \
    && cmake --build lept-build --parallel 2 \
    && cmake --install lept-build \
    && mkdir -p /opt/ocr/share/licenses/leptonica \
    && cp leptonica-1.87.0/leptonica-license.txt /opt/ocr/share/licenses/leptonica/LICENSE
# No OpenMP/GPL libgomp, network input, archive input or training tools in OCR.
RUN curl --fail --location https://github.com/tesseract-ocr/tesseract/archive/refs/tags/5.5.1.tar.gz -o tesseract.tar.gz \
    && tar -xzf tesseract.tar.gz \
    && cmake -S tesseract-5.5.1 -B build -DCMAKE_BUILD_TYPE=Release \
       -DCMAKE_INSTALL_PREFIX=/opt/ocr -DCMAKE_INSTALL_LIBDIR=lib -DCMAKE_PREFIX_PATH=/opt/ocr -DOPENMP_BUILD=OFF \
       -DDISABLE_CURL=ON -DDISABLE_ARCHIVE=ON -DGRAPHICS_DISABLED=ON \
       -DBUILD_TRAINING_TOOLS=OFF -DBUILD_TESTS=OFF -DBUILD_SHARED_LIBS=ON \
    && cmake --build build --parallel 2 \
    && cmake --install build \
    && mkdir -p /opt/ocr/share/licenses/tesseract \
    && cp tesseract-5.5.1/LICENSE /opt/ocr/share/licenses/tesseract/LICENSE

FROM python:3.14.5-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    OMP_THREAD_LIMIT=1 \
    FORMFORGE_OCR_LANGUAGES=pol+eng \
    PATH="/opt/ocr/bin:${PATH}" \
    LD_LIBRARY_PATH=/opt/ocr/lib \
    TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata

# Tesseract and language data are installed at BUILD time, never at request time.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpng16-16t64 libjpeg62-turbo zlib1g libstdc++6 tesseract-ocr-pol tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 formforge \
    && useradd --uid 10001 --gid formforge --no-create-home --shell /usr/sbin/nologin formforge

WORKDIR /app
COPY --from=ocr-builder /opt/ocr /opt/ocr
COPY requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock
COPY --chown=formforge:formforge formforge ./formforge
COPY --chown=formforge:formforge demo_samples ./demo_samples
COPY --chown=formforge:formforge config ./config
COPY --chown=formforge:formforge deploy ./deploy
COPY LICENSE THIRD_PARTY_NOTICES.md ./
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)"]
CMD ["python", "-m", "uvicorn", "formforge.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--limit-concurrency", "32"]
