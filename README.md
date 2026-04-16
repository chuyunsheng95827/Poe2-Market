# 游戏网页市集系统 - 课程设计项目

## 1. 项目简介

本项目是一个基于全栈技术实现的、针对《流放之路2》的虚拟物品交易市场分析系统。它通过一个创新的“人机协作”方案采集真实数据，并提供一个功能强大的Web界面，允许用户通过多重复杂条件对海量物品进行高级搜索、模拟添加和购买。

*   **后端技术:** Python, Flask, pyodbc, Microsoft SQL Server
*   **前端技术:** HTML, CSS, JavaScript, Vue.js, Axios
*   **核心特色:** 前后端分离架构，动态SQL查询构建，类表继承数据库范式，动态交互UI。

## 2. 环境要求

- **操作系统:** Windows 10 或更高版本
- **数据库:** Microsoft SQL Server 2017 或更高版本 (已安装并正在运行)
- **Python:** Python 3.8 或更高版本

## 3. 项目运行指南 (必读)

请严格按照以下步骤操作，以确保系统正常运行。

### **步骤一：数据库设置**

1.  打开 **SQL Server Management Studio (SSMS)** 并连接到您的数据库实例。
2.  在左侧“对象资源管理器”中，右键点击“数据库”，选择 **“还原数据库...”**。
3.  在“源”部分，选择 **“设备”**，然后点击“...”按钮，添加本项目`database/`目录下的 **`Poe2_MarketDB.bak`** 文件。
4.  点击“确定”完成还原。您应该能看到一个名为`Poe2_MarketDB`的新数据库。
5.  **（重要）** 打开 `backend/app.py` 文件，检查`DB_CONFIG`字典中的`server`值是否与您的SQL Server实例名称匹配。如果不同，请修改为您自己的实例名。

### **步骤二：启动后端API服务**

1.  打开一个命令行窗口 (CMD 或 PowerShell)。
2.  使用 `cd` 命令进入本项目的 `backend/` 目录。
3.  **（首次运行）** 建议创建并激活虚拟环境：
    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    ```
4.  **（首次运行）** 安装所有Python依赖：
    ```bash
    pip install -r requirements.txt
    ```
5.  启动后端服务器：
    ```bash
    python app.py
    ```
6.  看到 `* Running on http://127.0.0.1:5000` 输出后，**请保持此窗口不要关闭**。

### **步骤三：启动前端Web服务**

1.  **另外打开一个全新的**命令行窗口。
2.  使用 `cd` 命令进入本项目的 `frontend/` 目录。
3.  执行Python内置的HTTP服务器：
    ```bash
    python -m http.server 8000
    ```
4.  看到 `Serving HTTP on 0.0.0.0 port 8000 ...` 后，**请保持此窗口不要关闭**。

### **步骤四：访问系统**

1.  打开您的Web浏览器 (推荐使用Chrome)。
2.  在地址栏输入: **`http://localhost:8000/login.html`**
3.  使用测试账号登录 (用户名: `testuser`, 密码: `123456` - *请根据您在`Accounts`表中设置的实际密码填写*)。
4.  登录成功后，您将被自动跳转到主市集界面，可以开始进行所有操作。


---