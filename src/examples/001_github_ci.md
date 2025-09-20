# Github Actions工作流

GitHub Actions 工作流是一项强大的自动化工具，它允许你在 GitHub 仓库中自动执行软件开发生命周期中的各种任务，如构建、测试、打包、发布和部署。

### 基础介绍

#### 核心概念

GitHub Actions 的核心在于**工作流（Workflow）**，它是一个可配置的自动化过程，由一个或多个**作业（Jobs）** 组成，每个作业又包含一系列**步骤（Steps）**，这些步骤可以在特定**事件（Event）** 触发时在**运行器（Runner）** 上执行。

核心组件及其功能如下：

| 组件 (Component)      | 说明 (Description)                                           | 示例 (Example)                                    |
| :-------------------- | :----------------------------------------------------------- | :------------------------------------------------ |
| **工作流 (Workflow)** | 可配置的自动化过程，定义在 `.github/workflows`目录下的 YAML 文件中。 | `name: CI Pipeline`                               |
| **事件 (Event)**      | 触发工作流运行的特定活动，如推送代码、创建 PR 等。           | `on: [push, pull_request]`                        |
| **作业 (Job)**        | 一组在同一运行器上执行的步骤序列。一个工作流可以包含多个作业，默认并行执行，也可配置依赖关系串行执行。 | `jobs: build: runs-on: ubuntu-latest`             |
| **步骤 (Step)**       | 作业内的单个任务，可以运行命令或使用**操作（Action）**。     | `- name: Checkout code uses: actions/checkout@v3` |
| **操作 (Action)**     | 可重用的代码单元，是工作流的最小构建块，可用于简化复杂流程。 | `actions/checkout@v3`(检出代码)                   |
| **运行器 (Runner)**   | 执行工作流的服务器。可以是 GitHub 提供的**托管运行器**（如 Ubuntu, Windows, macOS），也可以是用户自己配置的**自托管运行器**。 | `runs-on: ubuntu-latest`                          |



#### 工作流文件结构

工作流文件采用 YAML 格式，通常包含以下部分：

- **`name`**: 工作流的名称。
- **`on`**: 指定触发事件，例如 `push`, `pull_request`, `schedule`(定时任务)，或 `workflow_dispatch`(手动触发)。
- **`jobs`**: 定义工作流中要执行的一个或多个作业。
  - **`runs-on`**: 指定作业运行的虚拟机环境。
  - **`steps`**: 定义作业中要执行的步骤序列。
    - **`uses`**: 使用一个现有的 Action。
    - **`run`**: 执行一个 shell 命令或脚本。
    - **`name`**: 步骤的名称，便于在日志中识别。
    - **`with`**: 为 Action 提供输入参数。
    - **`env`**: 为步骤设置环境变量。

简单的工作流示例：

```yaml
name: CI/CD Pipeline
on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up environment
        run: echo "Setting up environment"
      - name: Build
        run: echo "Building application"
      - name: Test
        run: echo "Running tests"
      - name: Deploy
        if: github.ref == 'refs/heads/main'
        run: echo "Deploying to production"
```



#### 主要应用场景

GitHub Actions 的应用场景非常广泛，主要包括：

- **持续集成 (CI)**：在代码提交后自动运行编译和测试，确保代码质量。例如，可以配置在每次推送代码或创建拉取请求时自动运行单元测试、集成测试。
- **持续部署 (CD)**：在代码通过测试后，自动部署到生产环境，如服务器、云平台（AWS、Azure）或容器平台（Kubernetes）。部署时可以结合策略如**蓝绿部署**或**金丝雀发布**以最小化风险。
- **自动化测试**：执行单元测试、集成测试、端到端测试等，并生成测试报告。
- **发布管理**：自动生成版本号、打包并发布到包管理器（如 npm、PyPI）。
- **自动化文档生成**：从代码注释自动生成 API 文档并部署到 GitHub Pages 等平台。
- **定期任务**：通过 `schedule`触发器执行定期任务，如清理缓存、安全检查等。



### 最佳实践

#### 矩阵构建

**矩阵构建（matrix strategy）** 允许你在多个操作系统、语言版本等不同配置下同时运行作业，这能有效测试代码的兼容性。示例如下：

```yaml
jobs:
  build:
    strategy:
      matrix:
        node-version: [14.x, 16.x, 18.x]
        os: [ubuntu-latest, windows-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v3
      - name: Use Node.js ${{ matrix.node-version }}
        uses: actions/setup-node@v3
        with:
          node-version: ${{ matrix.node-version }}
```



#### 缓存依赖

使用 `actions/cache`Action 缓存依赖项（如 `node_modules`或 Python 包），可以显著减少重复下载依赖的时间，加快工作流运行速度。示例如下：

```yaml
- name: Cache node modules
  uses: actions/cache@v3
  with:
    path: ~/.npm
    key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
    restore-keys: |
      ${{ runner.os }}-node-
```



#### 变量管理

##### secrets

**安全管理敏感信息**：**切勿**将密码、API 密钥等敏感信息直接写入工作流文件。应使用 GitHub 仓库设置中的 **Secrets** 功能安全地存储和引用它们。

Github Secrets允许你在仓库或组织级别加密存储敏感数据，这些数据在工作流运行时会通过环境变量注入，并且 GitHub 会自动屏蔽日志中的这些值以防泄露。支持创建如下三种Secret：

| 类型              | 创建位置                                        | 访问范围                               | 适用场景                                                     |
| :---------------- | :---------------------------------------------- | :------------------------------------- | :----------------------------------------------------------- |
| **仓库级 Secret** | 仓库 Settings → Secrets and variables → Actions | 仅限该仓库                             | 单个仓库专用的密钥，如部署到特定服务器的 SSH 私钥            |
| **组织级 Secret** | 组织 Settings → Secrets and variables → Actions | 组织内所有仓库或指定仓库               | 在多个仓库间共享的密钥，如统一的 Docker Hub 账号             |
| **环境级 Secret** | 仓库 Settings → Environments → 具体环境         | 需在作业中指定 `environment`时才可访问 | 为不同环境（如测试、生产）提供差异化配置，如生产环境的数据库密码 |



在工作流中使用Secrets：通过 ${{secrets.SECRET_NAME}}来引用配置的Secret

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    env: 
      # 在作业级别定义环境变量，所有步骤均可使用，不推荐
      DEPLOY_TOKEN: ${{ secrets.API_KEY }}
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: 使用环境变量示例
        run: echo "使用密钥进行操作" # 在脚本中通过 $DEPLOY_TOKEN 访问
       
      - name: 安全使用 Secret 示例
        env: 
          # 在步骤级别设置环境变量，推荐方式
          MY_SECRET: ${{ secrets.API_KEY }}
          DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
        run: |
          # 在脚本中使用环境变量，而不是直接引用 secrets
          curl -H "Authorization: Bearer $MY_SECRET" https://api.example.com/data
          ./my_script --db-pass="$DB_PASSWORD" # 通过参数传递也更安全

      - name: 直接引用 Secret
        run: echo "密钥是 ${{ secrets.API_KEY }}" # ❌ 不推荐，值虽会被屏蔽，但可能有日志泄露风险

      - name: 使用 SSH 连接到服务器
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SSH_USERNAME }}
          key: ${{ secrets.SSH_PRIVATE_KEY }} # 传递 SSH 私钥
          script: sudo deploy.sh
```



基于环境的条件访问：通过指定environment来使用该环境下配置的特定secrets

```yaml
jobs:
  deploy-prod:
    runs-on: ubuntu-latest
    environment: production # 指定环境，从而使用该环境下的 Secrets
    steps:
      - name: 部署到生产环境
        env:
          PROD_API_KEY: ${{ secrets.PROD_API_KEY }} # 使用 production 环境下的 Secret
        run: ./deploy.sh --env=production
```



在矩阵构建中动态选择secrets：利用矩阵策略和 `format`函数动态生成要引用的 Secret 名称

```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        env: [staging, production] # 定义矩阵变量
    steps:
      - name: 动态选择 Secret
        env:
          # 根据矩阵变量动态生成 Secret 名称，例如 secrets.STAGING_API_KEY 或 secrets.PROD_API_KEY
          API_KEY: ${{ secrets[format('{0}_API_KEY', matrix.env)] }}
        run: ./deploy.sh --env=${{ matrix.env }}
```



secrets 安全管理最佳实践：

1. **遵循最小权限原则**：只为 Secret 分配完成任务所需的最小权限

2. **严防日志泄露**

   + **避免在命令中直接输出**：如 `echo "${{ secrets.KEY }}"`。虽然 GitHub 会尝试屏蔽，但仍有风险。

   + **避免通过命令行参数传递**：命令行参数可能会被进程列表捕获。优先使用环境变量或配置文件。

     ```yaml
     # 不推荐
     - run: ./script.sh --password=${{ secrets.DB_PASSWORD }} # ❌
     
     # 推荐
     - env:
         DB_PASS: ${{ secrets.DB_PASSWORD }}
       run: ./script.sh # ✅ 脚本内部从 $DB_PASS 环境变量读取
     ```

3. **谨慎审核第三方 Actions**：在将 Secrets 传递给第三方 Actions（如 `with:`或 `env:`）时，务必审查其代码是否可信，防止恶意代码窃取密钥。

4. **处理 Pull Request 的安全**：来自外部分支的 Pull Request 默认无法访问仓库 Secrets。**切勿**在由 `pull_request`事件触发的工作流中执行敏感操作或访问 Secrets。应使用 `push`事件（例如在合并到主分支后）来触发部署流程。

5. **定期轮换密钥**：制定计划定期更新 Secrets（例如每 90 天）。你可以使用 GitHub API 和 Personal Access Token 自动化这一过程。

6. **审计与监控**：定期检查 GitHub 组织的审计日志，监控 Secrets 的创建、修改和访问情况。

7. **公共仓库禁用敏感 Secrets**：**绝对不要**在公共仓库中使用真正敏感的 Secrets，因为恶意用户可能通过构造特殊的工作流来窃取它们。



常见问题：

1. **Secret 未生效**：首先检查 Secret 名称的**拼写和大小写**是否与引用处完全一致。确认 Secret 已正确添加到预期的范围（仓库、组织或环境）。

2. **在 PR 中无法访问 Secret**：这是出于安全考虑的设计。如果确实需要，可考虑使用 `pull_request_target`事件，但务必了解其安全风险并添加额外防护条件（例如仅允许来自本仓库的 PR）。

3. **本地开发如何模拟**：在项目根目录创建 `.env`文件，并使用 `git update-index --assume-unchanged .env`或将其添加到 `.gitignore`中来避免提交。在工作流中，可以通过步骤生成这些环境变量。

   ```bash
   # .env 文件示例
   API_KEY=your_local_api_key_here
   DB_PASSWORD=your_local_db_password_here
   ```



##### vars

GitHub Actions 中的 `vars`上下文用于访问在**仓库级别、组织级别或环境级别**定义的**配置变量**。这些变量通常用于存储**非敏感**的配置信息，例如资源路径、功能标志或服务器名称。

| 方面                 | 说明                                                         | 示例或用法                                                   |
| :------------------- | :----------------------------------------------------------- | :----------------------------------------------------------- |
| **定义位置与优先级** | 变量可在**环境**、**仓库**、**组织**级别定义。**环境级**变量优先级最高，其次为**仓库级**，最后是**组织级**。 | 定义路径：仓库 Settings → Secrets and variables → Actions → Variables tab。 |
| **访问方式**         | 在工作流文件中使用 `${{ vars.VARIABLE_NAME }}`语法引用。     | `${{ vars.API_BASE_URL }}`                                   |
| **与 Secrets 区别**  | `vars`用于**非敏感**配置信息，值会以明文形式存储在日志中。**敏感信息**务必使用 `secrets`。 | 数据库密码应使用 `secrets`，部署环境标识可使用 `vars`。      |
| **常用场景**         | 配置不同环境（如开发、生产）的参数，设置构建标志，共享公共资源路径等。 | `environment: ${{ vars.ENVIRONMENT }}`                       |



定义配置变量：

1. **仓库级别**：在仓库的 **Settings > Secrets and variables > Actions > Variables** 标签页下，点击 **New repository variable** 来添加。此变量仅对该仓库可见。
2. **组织级别**：在组织的 **Settings > Secrets and variables > Actions > Variables** 标签页下，点击 **New organization variable** 来添加。你可以选择让变量对所有仓库可见，或仅限选择的仓库。
3. **环境级别**：在仓库的 **Settings > Environments** 下，选择或创建一个环境，然后在其 **Environment variables** 部分添加。此变量仅对引用该环境的工作流作业可见。



变量名称限制：

- 名称只能包含字母数字字符（`[a-z]`, `[A-Z]`, `[0-9]`）或下划线（`_`）。
- 不能以 `GITHUB_`前缀开头。
- 不能以数字开头。
- 不区分大小写。
- 在创建它的仓库、组织或环境中必须唯一。



配置变量数量和大小限制：

- 单个变量大小限制为 **48 KB**。
- 一个组织最多可存储 **1,000** 个变量，一个仓库最多 **500** 个变量，一个环境最多 **100** 个变量。
- 组织和仓库变量的总大小限制为每个工作流运行 **10 MB**（环境级别变量不计入此限制）。



工作流中变量使用示例：

```yaml
name: Deployment
on:
  workflow_dispatch: # 手动触发工作流
env:
  # 可以从 vars 中取值来设置环境变量
  DEPLOYMENT_ENV: ${{ vars.ENVIRONMENT }}
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: ${{ vars.ENVIRONMENT }} # 使用变量指定环境
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Debug variables
        run: |
          echo "Deploying to: $DEPLOYMENT_ENV"
          echo "API URL: ${{ vars.API_BASE_URL }}"
          echo "Max retries: ${{ vars.MAX_RETRIES }}"

      - name: Deploy to server
        if: ${{ vars.SHOULD_DEPLOY == 'true' }} # 使用变量控制步骤执行
        run: ./deploy.sh --env $DEPLOYMENT_ENV
```



注意事项：

1. **变量优先级**：如果同名变量在多个级别定义，**环境级**变量优先级最高，其次是**仓库级**，最后是**组织级**。
2. **可重用工作流**：在可重用工作流中，使用的是**调用方**工作流仓库的变量。被调用工作流仓库中定义的变量对调用方不可用。
3. **默认环境变量**：GitHub 还提供了一系列默认环境变量（如 `GITHUB_REPOSITORY`），它们与 `vars`上下文不同，通常以 `GITHUB_`或 `RUNNER_`开头，并且是只读的。





##### secrets、vars、env对比

| 特性         | `vars`(配置变量)       | `env`(环境变量)                     | `secrets`(机密)              |
| :----------- | :--------------------- | :---------------------------------- | :--------------------------- |
| **用途**     | 非敏感配置             | 主要在工作流内部定义非敏感数据      | **敏感信息**（如密钥、令牌） |
| **定义位置** | 仓库、组织、环境设置   | 工作流文件内部 (`env`关键字)        | 仓库、组织、环境设置         |
| **访问方式** | `${{ vars.VAR_NAME }}` | `${{ env.VAR_NAME }}`或 `$VAR_NAME` | `${{ secrets.SECRET_NAME }}` |
| **日志显示** | **明文显示**           | 明文显示（除非手动屏蔽）            | **自动屏蔽**                 |
| **适用范围** | 可跨仓库（组织变量）   | 仅限于定义它的工作流、作业或步骤    | 可跨仓库（组织机密）         |

最佳实践：

- **绝不**将密码、API 密钥等敏感信息存入 `vars`，务必使用 `secrets`。
- 对于需要在不同工作流或仓库间共享的**非敏感**配置，`vars`（特别是组织变量）非常有用。
- 对于工作流**内部**使用的临时变量或脚本使用的变量，使用 `env`更合适。



#### 优化工作流结构

- 使用 `needs`关键字来定义作业之间的依赖关系，确保它们按顺序执行。
- 使用 `if`条件语句来控制步骤或作业仅在特定条件下运行。
- 将复杂的工作流分解为多个更小、更专注的工作流文件。
- 为长时间运行的作业设置 `timeout-minutes`，避免资源浪费。



#### 查看日志和调试

作流运行后，可以在 GitHub 仓库的 "Actions" 标签页下查看详细日志，这有助于排查失败原因。可以使用 `actions/upload-artifact`Action 上传构建产物或日志文件以便进一步分析。



### 部署模式

Github Actions的自动化部署流程主要支持如下两种部署方式：

```mermaid
flowchart TD
A[代码推送事件触发] --> B[构建阶段<br>检出代码、安装环境、执行构建]
B --> C{选择部署方式}
    
C --> D[传统方式: gh-pages分支]
D --> D1[推送构建产物<br>到gh-pages分支]
D1 --> D2[GitHub Pages自动<br>从gh-pages分支部署]
D2 --> F[部署完成]
    
C --> E[现代方式: Pages Artifact]
E --> E1[上传构建产物<br>为Artifact]
E1 --> E2[Deploy Pages Action<br>读取Artifact并部署]
E2 --> F
    
F --> G[通知与监控]
```

#### 部署到gh-pages分支

部署到gh-pages是早期的主流做法，通过将构建的好的静态文件推送到仓库内一个单独的gh-pages分支来实现部署。主要特点如下：

- 优点：配置简单，兼容大量旧项目和教程
- 缺点：