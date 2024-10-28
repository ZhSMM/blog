# Stable Diffusion WebUI

#### 安装

Stable Diffusion webUI 

Github 仓库：[https://github.com/AUTOMATIC1111/stable-diffusion-webui](https://github.com/AUTOMATIC1111/stable-diffusion-webui)

Windows自动安装：

1. 下载sd.webui.zip并解压：[https://github.com/AUTOMATIC1111/stable-diffusion-webui/releases/download/v1.0.0-pre/sd.webui.zip](https://github.com/AUTOMATIC1111/stable-diffusion-webui/releases/download/v1.0.0-pre/sd.webui.zip)
2. 运行解压目录下的 update.bat
3. 运行解压目录下的 run.bat
4. 执行成功后，浏览器访问：[http://127.0.0.1:7860](http://127.0.0.1:7860)

启动参数配置，在解压目录 `webui\webui-user.bat` 中添加如下参数，更多优化参数说明：[https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/Optimizations](https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/Optimizations)

```ini
# --autolaunch：Web UI 在启动后自动启动 Web 浏览器
# --update-check：在启动时检查 Web UI 的新版本
# --xformers：使用xFormers库，改善内存消耗和生成速度
set COMMANDLINE_ARGS=--autolaunch --update-check --xformers
```



运行碰到的问题：在浏览器打开 http://127.0.0.1:7860 时，在页面上任意交互操作都提示`Something went wrong Expecting value: line 1 column 1 (char 0)`

解决办法：关闭VPN工具或在 `...\webui\webui-user.bat` 添加启动参数：--no-gradio-queue



#### 模型资源下载网站

常用的绘画模型下载站：

+ civitai：[https://civitai.com/models](https://civitai.com/models)
+ Hugging Face：[https://huggingface.co/](https://huggingface.co/)
+ 哩布哩布：[https://www.liblib.art/](https://www.liblib.art/)

在线工具：

+ [https://app.anakin.ai/](https://app.anakin.ai/)



#### 汉化

汉化插件：[https://github.com/VinsonLaro/stable-diffusion-webui-chinese](https://github.com/VinsonLaro/stable-diffusion-webui-chinese)

安装方式：

1. 打开stable diffusion webui，进入"Extensions"选项卡

2. 点击"Install from URL"，注意"URL for extension's git repository"下方的输入框

3. 粘贴或输入Git仓库地址`https://github.com/VinsonLaro/stable-diffusion-webui-chinese`

4. 点击下方的黄色按钮"Install"即可完成安装，然后重启WebUI(点击"Install from URL"左方的"Installed"，然后点击黄色按钮"Apply and restart UI"网页下方的"Reload UI"完成重启)

5. 点击"Settings"，左侧点击"User interface"界面，在界面里最下方的"Localization (requires restart)"，选择"Chinese-All"或者"Chinese-English"

6. 点击界面最上方的黄色按钮"Apply settings"，再点击右侧的"Reload UI"即可完成汉化



#### 模型分类

+ Checkpoint：Stable Diffusion绘图的基础模型，因此被称为大模型、底模型或者主模型。在WebUI上，它被称为Stable Diffusion模型。安装完Stable Diffusion软件后，必须搭配主模型才能使用。
  + Checkpoint模型可以直接生成图像，而不需要额外的文件，一般为2GB～7GB
  + Checkpoint模型主要有两种后缀名，safetensor和ckpt，存放在`webui\models\Stable-diffusion`
  + 不同的模型库具有不同的风格，常见的风格有GhostMix（带科技感的2.5D风格）、Counterfeit（二次元卡通风格）、ChilloutMix（写实风格）
+ LoRA：微调模型，可以固定某一类型的人物或者画面的风格。这些模型的文件大小通常为10 MB～200 MB，必须与Checkpoint模型一起使用，支持如下两种使用方式
  + 在插件中使用，放在`webui\extensions`
  + 在提示词中使用，放在`webui\models\lora` 
+ LyCORIS模型：它可以让LoRA学习更多的层，可以看作升级的LoRA，归类为LoRA模型，属于微调模型的一种
+ Controlnet模型：它是一种神经网络结构，通过添加额外的条件来控制扩散模型
+ Textual Inversion模型（也称为Embedding）：它是一种用于定义新关键词以生成新人物或图像风格的小文件，它也属于微调模型，用于个性化图像的生成。该模型的安装目录为`webui\models\Embedding`
+ Hypernetwork模型：它是添加到Checkpoint模型中的附加网络模块，是个性化模型的一种。该模型的安装目录为`webui\models\hypernetworks`
+ VAE模型：全称为Variational Autoencoder，中文叫变分自编码器。它的作用是滤镜+微调。大部分主模型训练时自带了VAE，它是一种美化模型，比如我们常用的ChilloutMix主模型，如果再加VAE美化模型可能图像效果会适得其反。如果我们生成的图像颜色不正常，就需要检查主模型配套的VAE模型



#### 功能选项卡说明

