# 三国杀阿超钓鱼脚本

## **项目简介**: 

这是是一个自动化脚本，通过模拟鼠标操作，实现自动钓鱼，解放双手
初版代码来源于 https://github.com/KeNanXiaoLin/sgsminigame

## **使用步骤**

1.**克隆代码** 

将代码克隆到本地电脑。

```bash
git clone https://github.com/vibesudi/SgsAutoFish.git
```

2.**安装环境**

下载 Python 3.13.0，安装 `requirements.txt` 中的库。

```bash
pip3 install -r requirements.txt
```

3.**运行脚本**: 

在模拟器中打开三国杀阿超钓鱼界面，运行 `main.py` 文件，即可开始自动钓鱼。

![image](images/description_images/diaoyu.png)

就是这个界面，然后就可以再次运行main.py就可以了。

4.**ESC 退出**: 

**配置文件中的参数说明**:

**生成配置文件**

运行 `main.py` 文件，会在项目同级目录下会生成 `config.yaml` 配置文件。

只有两个默认参数，模拟器大小和模拟器名称.

模拟器窗口大小不用管，窗口标题需要自己修改，改成使用的模拟器名。

比如使用的是雷电模拟器，名称就是雷电模拟器，如果是的，就个改名就可以了
