from setuptools import setup, find_packages

setup(
    name="ouh_inference",
    version="0.1.0",
    description="Command line tool for starting an inference process. Mainly called by a service of our OUH AI Inference Service.",
    url="http://srvodeapprfl01v:3000/RadFys/ouh_ai_inference_process",
    author="Maximilian Lukas Konrad",
    email="maximilian.lukas.konrad@rsyd.dk",
    license="MIT",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "ouh_inference=InferenceProcess.main:main",
        ],
    },
)
