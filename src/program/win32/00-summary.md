# win32编程

Windows程序分类：

+ Console 控制台程序：入口函数main
+ 窗口程序：入口函数WinMain
+ 库程序：存放代码、数据的程序，执行文件可以从中取出代码执行和获取数据
  + 静态库：扩展名 lib，在编译链接程序时，将代码放入到可执行文件，无入口函数
  + 动态库：扩展名 dll，在执行文件执行时从中获取代码，入口函数DllMain

编译工具：

+ 编译器：cl.exe，将源代码编译成目标代码，扩展名.obj
+ 链接器：link.exe，将目标代码、库链接生成最终文件
+ 资源编译器：rc.exe，将.rc资源编译，最终通过链接器存入最终文件

Windows库文件：C:\Windows\System32

+ kernel32.dll：提供了核心的API，如进程、线程、内存管理等
+ user32.dll：提供了窗口、消息等API
+ gdi32.dll：绘图相关的API

头文件：

+ windows.h：所有windows头文件的集合
+ windef.h：windows数据类型
+ winbase.h：kernel32的API
+ wingdi.h：gdi32的API
+ winuser.h：user32的API
+ winnt.h：UNICODE字符集支持

相关函数：

```c++
int WINAPI WinMain(
	HINSTANCE hInstance, // 当前程序的实例句柄
	HINSTANCE hPrevInstance, // 当前程序前一个实例句柄
    LPSTR lpCmdLine, // 命令行参数字符串
    int nCmdShow // 窗口的显示方向
);

int MessageBox(
	HWND hWnd, // 父窗口句柄
    LPCTSTR lpText, // 显示在消息框中的文字
    LPCTSTR lpCaption, // 显示在标题栏中的文字
    UINT uType // 消息框中的按钮、图标显示类型
); // 返回点击的按钮ID
```



##### win32编译过程示例

示例：将下面内容保存为main.cpp

```c++
#include <windows.h>

int WINAPI WinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, LPSTR lpCmdLine, int nCmdShow) {
    MessageBox(NULL, TEXT("hello world"), TEXT("EN"), MB_YESNOCANCEL|MB_ICONWARNING);
    return 0;
}
```

通过[https://convertio.co/zh](https://convertio.co/zh)转换获得一张ico文件，命名为main.ico，并创建main.rc：

```rc
100 ICON main.ico
```

在命令行进行编译链接生成一个带图标的应用程序：

```shell
# 加载编译环境，执行vcvars32.bat脚本
"C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars32.bat"

# 编译程序，生成main.obj
cl.exe -c main.cpp /utf-8

# 编译资源文件，生成main.res
rc.exe main.rc

# 链接程序，链接完成后生成可执行exe文件
link.exe main.obj user32.lib main.res
```

通过上面的示例，可以看出windows上的编译过程：

```
            cl.exe
.c/.cpp -------------> .obj |      link.exe
            rc.exe          | -------------> .exe
.rc     -------------> .res |
```



##### 字符编码

char、wchar_t与TCHAR：

+ char：每个字符占1个字节

+ wchar_t：unsigned short，每个字符占用2个字节，定义时需要增加L，用于通知编译器按照双字节编码字符串，采用UNICODE编码

  ```
  // 需要使用支持wchar_t函数操作宽字节字符串
  wchar_t* pwszText = L"Hello world";
  wprintf(L"%s\n", pwszText);
  ```

+ TCHAR：宏，根据是否定义UNICODE宏来处理字符串

  ```c++
  void print() {
      TCHAR* cs = __TEXT("hello world");
  #ifdef UNICODE
      wprintf(L"%s\n", cs);
  #else
      printf("%s\n", cs)
  #endif
  }
  ```

unicode字符打印：wprintf对unicode字符打印支持不完善，在Windows下使用WriteConsole API（GetStdHandle）印unicode字符

```c++
wchar_t* pszText = L"中文";
HANDLE hOut = GetStdHandle(STD_OUTPUT_HANDLE);
// 标准输出句柄，缓冲区，输出长度
WriteConsole(hOut, pszText, wcslen(pszText), NULL, NULL);
```



在Windows下，很多系统调用函数参数类型如下：

```
LPSTR  == char*      LPCSTR  == const char*
LPWSTR == wchar_t*   LPCWSTR == const wchar_t*
LPTSTR == TCHAR*     LPCTSTR == const TCHAR*
```

使用VS开发时，可以在项目上右键，选择属性，进入属性页后，选择高级，将字符集由默认的“使用Unicode字符集”切换成“使用多字节字符集”，这样编译器不会自动定义UNICODE宏，从而在调用系统LPTSTR参数时，不需要传入宽字符。



##### win32窗口程序开发

win32窗口创建过程：

1. 定义WinMain函数
2. 定义窗口处理函数（自定义，处理数据）
3. 注册窗口类（向操作系统写入一些数据）
4. 创建窗口（内存中创建窗口）
5. 显示窗口（绘制窗口的图像）
6. 消息循环（获取/翻译/派发消息）
7. 消息处理

