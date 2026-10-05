FROM public.ecr.aws/lambda/python:3.12
ENV HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false
RUN pip install --no-cache-dir torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu && pip install --no-cache-dir transformers==4.57.6
COPY . ${LAMBDA_TASK_ROOT}
RUN HF_HUB_DISABLE_XET=1 HF_HUB_OFFLINE=0 TRANSFORMERS_OFFLINE=0 python -c "from huggingface_hub import snapshot_download; snapshot_download('Qwen/Qwen2.5-0.5B-Instruct',revision='7ae557604adf67be50417f59c2c2f167def9a775',local_dir='/var/task/model',allow_patterns=['*.json','*.safetensors','*.txt'])" && rm -rf /root/.cache/huggingface
CMD ["deploy.model_handler.handler"]
