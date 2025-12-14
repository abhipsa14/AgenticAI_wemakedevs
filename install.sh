#!/bin/bash
# Install packages one at a time to reduce peak memory usage

pip install --no-cache-dir --prefer-binary pydantic==2.5.3
pip install --no-cache-dir --prefer-binary pydantic-settings==2.1.0
pip install --no-cache-dir --prefer-binary fastapi==0.109.0
pip install --no-cache-dir --prefer-binary python-multipart==0.0.6
pip install --no-cache-dir --prefer-binary python-dotenv==1.0.0
pip install --no-cache-dir --prefer-binary jinja2==3.1.2
pip install --no-cache-dir --prefer-binary aiofiles==23.2.1
pip install --no-cache-dir --prefer-binary sqlmodel==0.0.14
pip install --no-cache-dir --prefer-binary pypdf==3.17.4
pip install --no-cache-dir --prefer-binary httpx==0.26.0
pip install --no-cache-dir --prefer-binary openai==1.6.1
