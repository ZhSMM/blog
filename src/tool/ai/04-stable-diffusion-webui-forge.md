# Stable Diffusion WebUI forge部署Flux模型

### Stable Diffusion WebUI Forge下载

Stable Diffusion WebUI Forge Github网址：[https://github.com/lllyasviel/stable-diffusion-webui-forge](https://github.com/lllyasviel/stable-diffusion-webui-forge)

下载：[根据当前机器的CUDA版本](./03-cuda-install.md)，选择合适的安装包，此处选择推荐包

![image-20241029235751395](./images/image-20241029235751395.png) 

下载完成后，先执行update.bat脚本，再执行run.bat脚本。



### Flux模型

参考：[https://www.youtube.com/watch?v=pC2H_GGyuUU](https://www.youtube.com/watch?v=pC2H_GGyuUU)

#### 下载Flux官方FP16模型

Flux模型说明页面：[https://github.com/lllyasviel/stable-diffusion-webui-forge/discussions/1050](https://github.com/lllyasviel/stable-diffusion-webui-forge/discussions/1050)

![image-20241030223454446](./images/image-20241030223454446.png) 



1、下载基础模型和vae：

+ 开发版：[https://huggingface.co/black-forest-labs/FLUX.1-dev/tree/main](https://huggingface.co/black-forest-labs/FLUX.1-dev/tree/main)
+ 极速版：[https://huggingface.co/black-forest-labs/FLUX.1-schnell](https://huggingface.co/black-forest-labs/FLUX.1-schnell)

![image-20241030224049688](./images/image-20241030224049688.png) 

下载上图圈出来的两个文件，并放置到安装目录：

+ flux1-schnell.safetensors 放到 models\Stable-diffusion 目录
+ ae.safetensors 放到 models\VAE 目录



2、下载clip-l和t5：

+ 原仓库地址：[https://huggingface.co/comfyanonymous/flux_text_encoders/tree/main](https://huggingface.co/comfyanonymous/flux_text_encoders/tree/main)
+ 镜像仓地址：[https://huggingface.co/lllyasviel/flux_text_encoders/tree/main](https://huggingface.co/lllyasviel/flux_text_encoders/tree/main)

![image-20241030224809869](./images/image-20241030224809869.png) 

下载圈起来的三个文件，并全部放到 models\text_encoder 目录



#### 下载精简FP8模型

##### Kijai版大模型

下载地址：[https://huggingface.co/Kijai/flux-fp8/tree/main](https://huggingface.co/Kijai/flux-fp8/tree/main)

![image-20241030225307626](./images/image-20241030225307626.png) 

下载后放到 models\Stable-diffusion 目录



##### Comfy UI版

下载地址：[https://huggingface.co/Comfy-Org/flux1-schnell/tree/main](https://huggingface.co/Comfy-Org/flux1-schnell/tree/main)

![image-20241030225449748](./images/image-20241030225449748.png) 

下载后放到 models\Stable-diffusion 目录



#### 下载GGUF模型（适合显存较小的用户）

说明页：[https://github.com/lllyasviel/stable-diffusion-webui-forge/discussions/1050](https://github.com/lllyasviel/stable-diffusion-webui-forge/discussions/1050)

![image-20241030225700198](./images/image-20241030225700198.png) 

下载GGUF模型：

+ 开发版：[https://huggingface.co/lllyasviel/FLUX.1-dev-gguf](https://huggingface.co/lllyasviel/FLUX.1-dev-gguf)
+ 极速版：[https://huggingface.co/lllyasviel/FLUX.1-schnell-gguf](https://huggingface.co/lllyasviel/FLUX.1-schnell-gguf)

![image-20241030230004671](./images/image-20241030230004671.png)  

下载文件放在 models\Stable-diffusion 目录



#### 下载NF4

说明页：[https://github.com/lllyasviel/stable-diffusion-webui-forge/discussions/981](https://github.com/lllyasviel/stable-diffusion-webui-forge/discussions/981)

![image-20241030230845980](./images/image-20241030230845980.png) 

+ 30、40系显卡：[https://huggingface.co/lllyasviel/flux1-dev-bnb-nf4/blob/main/flux1-dev-bnb-nf4-v2.safetensors](https://huggingface.co/lllyasviel/flux1-dev-bnb-nf4/blob/main/flux1-dev-bnb-nf4-v2.safetensors)
+ 其他显卡：[https://huggingface.co/lllyasviel/flux1_dev/blob/main/flux1-dev-fp8.safetensors](https://huggingface.co/lllyasviel/flux1_dev/blob/main/flux1-dev-fp8.safetensors)

下载完成后，放入 models\Stable-diffusion 目录



#### Flux模型使用说明

Flux1-SCHNELL、KIJAI、GGUF使用时需要配套开启clip和vae；而ComfyUI和NF4已经融合了clip和vae，可以直接出图。
