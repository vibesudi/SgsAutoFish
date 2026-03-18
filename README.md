# 三国杀阿超钓鱼脚本

## **项目简介**: 

这是是一个自动化脚本，通过模拟鼠标操作，实现自动钓鱼，解放双手
初版代码来源于 
- https://github.com/KeNanXiaoLin/sgsminigame
- https://github.com/Elevo4/TKAutoFisher

## **使用步骤**：
- 程序准备好后，模拟器(我用的MuMu)重命名为 **"ABC"**，打开三国杀阿超钓鱼开始钓鱼界面，运行程序
- **Esc** 键退出

### 方案一 ：
- 直接下载dist目录下 **AutoFish.exe**

### 方案二：开发调式

1.**克隆代码** 

将代码克隆到本地电脑。

```bash
git clone https://github.com/vibesudi/SgsAutoFish.git
```

2.**安装环境**

下载 **Python 3.13.0**，安装 `requirements.txt` 中的库。如果报错，大概率是缺少库，或版本不匹配。根据错误提示，安装缺少的库。

```bash
pip3 install -r requirements.txt
```

4.**运行脚本**: 

模拟器重命名为 "ABC", 打开三国杀阿超钓鱼界面，运行 `main.py` 文件，即可开始自动钓鱼。

![image](images/description_images/diaoyu.png)

5.**配置文件中的参数说明**:

**生成配置文件**

运行 `main.py` 文件，会在项目同级目录下会生成 `config.yaml` 配置文件。

只有两个默认参数，模拟器大小和模拟器名称.

模拟器窗口大小不用管，窗口标题需要自己修改，改成使用的模拟器名。

比如使用的是雷电模拟器，名称就是雷电模拟器

4.**打包 exe**: 
```
pyinstaller -F -w --add-data "images;images" --add-data "generate/config.yaml;generate" -i app.ico -n AutoFish main.py
```