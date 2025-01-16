from setuptools import setup, find_packages

# 读取版本信息
with open('story_generation/__init__.py', 'r', encoding='utf-8') as f:
    for line in f:
        if line.startswith('__version__'):
            version = line.split('=')[1].strip().strip('"\'')
            break

# 读取依赖
with open('requirements.txt', 'r', encoding='utf-8') as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

# 读取长描述
with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name="story_generation",
    version=version,
    packages=find_packages(include=['story_generation', 'story_generation.*']),
    install_requires=requirements,
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-asyncio>=0.21.0',
            'black>=23.0.0',
            'isort>=5.0.0',
            'mypy>=1.0.0',
        ],
    },
    python_requires=">=3.8",
    author="Codeium",
    author_email="support@codeium.com",
    description="An AI-powered story generation system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords="story, generation, AI, LLM",
    project_urls={
        "Source": "https://github.com/codeium/story-generation",
        "Documentation": "https://docs.codeium.com/story-generation",
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Text Processing :: General",
    ],
)
