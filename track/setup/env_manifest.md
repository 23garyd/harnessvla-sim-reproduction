# Environment manifest

Generated 2026-07-26T23:54:01Z by `track/setup/gen_env_manifest.sh`.

## Host
- OS: Ubuntu 22.04.2 LTS (6.8.0-111-generic)
- GPU 0: NVIDIA RTX A6000, 570.153.02, 49140 MiB
- CUDA (driver): CUDA Version: 12.8
- Python: Python 3.10.19

## Repos
- track repo: c2fdfad98ccd981c761d3b859d69f49a892fc04f
- RPent: 6e4ba1805a459d74ad53569e833bae7ae2c59985 (https://github.com/RLinf/RPent, pinned in pins.env)

## Key packages (full resolution: requirements.lock)
- jax==0.5.3
- jax-cuda12-pjrt==0.5.3
- jax-cuda12-plugin==0.5.3
- jaxlib==0.5.3
- jaxtyping==0.2.36
- lerobot==0.1.0
- mujoco==3.8.1
- rlinf-libero==0.1.1
- rlinf-openpi==0.1.0
- rlinf-transformer-openpi==4.53.2
- robosuite==1.4.1
- rpent==0.0.0
- rpent-liberopro==0.1.1
- rpent-rlinf==0.3.0
- torch==2.7.1
- torchvision==0.22.1
- lerobot origin: https://github.com/huggingface/lerobot@0cf864870cf29f4738d3ade893e6fd13fbd7cdb5

## Checkpoint
- source: RLinf/RLinf-Pi05-LIBERO-130-fullshot-SFT (HF **model** repo; the internship plan's dataset URL is wrong)
- local: checkpoints/rlinf-pi05-libero-130-fullshot-sft
- sha256:

    11ad7efa24975ee4b0c3c3a38ed18737f0658a5f75a0a96787b576a78a023361  ./.gitattributes
    8eba92f1159903755c6f529320913033a142a691bb148f90a96db0b6b91d6528  ./metadata.pt
    4d9089c941793f170b625c2ed0ac7a3aa09b6f103e52dbbc82e67301529d6683  ./model.safetensors
    7577d0287e0f77b735f39e76c7e656bf6fc1da5c7c424fbe9037ade622df83bc  ./optimizer.pt
    dae37d79a22108af83df9189c6710a3ec8e077d65b28e34bdf1da724e5ae30f1  ./physical-intelligence/libero/norm_stats.json
