# Windows上安装CUDA

在Windows上安装CUDA：

1、根据显卡型号更新显卡驱动：[https://www.nvidia.cn/drivers/lookup/](https://www.nvidia.cn/drivers/lookup/)

![image-20240810164726532](images/image-20240810164726532.png) 

2、在cmd窗口输入`nvidia-smi`，其中CUDA Version表示当前驱动支持的最新版本：

![image-20240810165026673](images/image-20240810165026673.png) 

3、进入CUDA下载页面，下载小于等于上述显示版本的CUDA：[https://developer.nvidia.com/cuda-toolkit-archive](https://developer.nvidia.com/cuda-toolkit-archive)

![image-20240810171018208](images/image-20240810171018208.png) 

并跟据操作系统和架构选择对应的安装包下载安装：

![image-20240810171114654](images/image-20240810171114654.png) 

在cmd窗口输入`systeminfo`可以查看操作系统的架构：

![image-20240810171359972](images/image-20240810171359972.png) 

4、在cmd窗口输入`nvcc -V`，如果正常输出版本号则安装成功：

 ![image-20240815231055850](images/image-20240815231055850.png) 
