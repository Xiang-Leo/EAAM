# EAAM Database (Ancient Calculus Microbiome)

## 1. 项目简介
EAAM (East Asian Ancient Microbiome) 研究数据库是一个专为展示和分析**中国古代牙结石微生物组（Ancient Chinese Dental Calculus Microbiome）**数据而设计的综合性分析平台。项目结合了现代前后端技术与数据处理流水线，旨在让科研人员和考古学家能够直观地在宏观时间尺度（朝代）、地理空间尺度（省份/大区）以及人类行为尺度（生业模式）下，探索古代微生物群落的时空演化。

## 2. MVP 功能
当前版本（MVP，Minimum Viable Product）已实现以下核心功能：
- **数据自动化清洗与导入**：支持将宽表格式的 Kraken2 原始分析结果自动化转化为适合关系型数据库的长表，并进行自动验证与导入。
- **全局大盘监控**：直观展示数据库收录的古代样品数、分类单元数，以及跨朝代、跨地域的宏观分布柱状图。
- **样品追踪与检索**：支持对所有入库样品的四维联合筛选（朝代、省份、性别、生业模式），并可一键钻取具体样品的专属微生物丰度组成。
- **Top Taxa 跨组探索**：允许用户在指定过滤条件下，查看某种级别（如属级、种级）下最具有优势的微生物类群。
- **特定物种深度分布**：提供向导式的查询能力，深入剖析某一特定微生物在各个朝代、地区的组间丰度差异。
- **基于规则引擎的 AI Agent 雏形**：解析自然语言查询意图并自动推断关联的数据端点。

---

## 3. 数据输入格式
项目依赖于存放在 `data/raw/` 目录下的两个原始输入文件：
1. **`samples.csv`**: 样品的 Meta 数据（元数据）。
2. **`kraken2_raw.tsv`**: 生物信息分析流水线产出的 Kraken2 宽表数据。

## 4. `samples.csv` 字段说明
| 字段名 | 说明 |
|---|---|
| `sample_id` | 样品的唯一编号，**必须与 Kraken2 数据中的样本前缀保持一致**（例如：GX_Tang_1）。 |
| `province` | 发掘省份（如：Shaanxi, Henan）。 |
| `region` | 所属大区（如：North, Northwest）。 |
| `dynasty` | 所属历史朝代（如：Tang, Han, Ming）。 |
| `period` | 更详细的历史时期阶段标识。 |
| `estimated_year` | 估算的绝对年代（通常结合碳十四测年数据）。 |
| `sex` | 性别判定（`M`, `F`, `Unknown`）。 |
| `subsistence_pattern`| 人群的生业模式（如：Agriculture 农业, Pastoralism 畜牧业, Foraging 采集）。 |
| `site_name` | 考古遗址名称。 |
| `latitude` / `longitude` | 遗址经纬度坐标。 |
| `source` | 样本来源或参考文献引用。 |

## 5. `kraken2_raw.tsv` 字段说明
Kraken2 产出的宽表。对于每一个样品会有两列，以 `_all` 和 `_lvl` 结尾：
| 字段名 | 说明 |
|---|---|
| `{sample_id}_all` | 该样品在该分类节点（Clade）下及其所有子节点累计比对上的 Reads 绝对数量。 |
| `{sample_id}_lvl` | 该样品**仅**精确比对到该分类节点（Level/Taxon）的 Reads 绝对数量。 |
| `lvl_type` | 分类层级缩写（U: Unclassified, R: Root, D: Domain, P: Phylum, C: Class, O: Order, F: Family, G: Genus, S: Species）。 |
| `taxid` | NCBI 分类数据库的全局唯一 Tax ID。 |
| `name` | 该分类节点的科学名称（Taxon Name）。 |

---

## 6. 数据处理流程
数据必须经过以下脚本的依次处理才能送入后端数据库使用：

1. **`convert_kraken2_to_long.py` (宽表转长表)**
   ```bash
   python scripts/convert_kraken2_to_long.py
   ```
   **功能**：自动读取 `data/raw/kraken2_raw.tsv`，识别所有的 `_all` 和 `_lvl` 样品列，并将其透视为长表格式（一行代表一个 Sample × Taxon）。自动计算相对丰度（`relative_abundance_all` 和 `relative_abundance_lvl`）。

2. **`validate_data.py` (数据一致性校验)**
   ```bash
   python scripts/validate_data.py --samples data/raw/samples.csv --abundance data/processed/taxonomy_abundance_long.csv
   ```
   **功能**：检查样品字典与丰度表中的 `sample_id` 是否可以无缝对应，同时验证相对丰度是否收敛于 `[0, 1]`。检查结果将输出至 `data/processed/validation_report.txt`。

3. **`import_to_db.py` (入库脚本)**
   ```bash
   python scripts/import_to_db.py --reset
   ```
   **功能**：将验证通过的长表数据与样品 Meta 数据导入后端的 SQLite 数据库（使用 `--reset` 参数可以抹除原有数据从头导入），并在终端显示导入量统计。

---

## 7. 后端启动方式
后端服务采用 Python + FastAPI 构建：
```bash
cd backend
# 激活虚拟环境 (可选)
python -m venv .venv
source .venv/bin/activate
# 安装依赖
pip install -r requirements.txt
# 启动热重载开发服务器
uvicorn app.main:app --reload
```
API 服务将运行在 `http://localhost:8000`。
你可以在 `http://localhost:8000/docs` 访问全自动生成的 Swagger 交互式文档。

## 8. 前端启动方式
前端采用 Next.js 14 + React + Tailwind CSS 构建：
```bash
cd frontend
# 安装 Node.js 依赖
npm install
# 启动本地开发服务器
npm run dev
```
网站将运行在 `http://localhost:3000`。

## 9. Docker 启动方式
为方便服务器部署，本仓库提供了一键容器化配置方案：
```bash
# 根目录下执行（请确保已基于 .env.example 建立 .env 文件，并配置正确）
docker compose up --build
```
执行完毕后：
- 前端页面: `http://localhost:9039`
- 后端 API: `http://localhost:9040`

前端默认通过同源 `/api/*` 访问接口，并由 Next.js 容器代理到后端容器
`http://backend:8000`。部署到 ECS 时，浏览器只需要能访问前端地址
`http://<服务器公网 IP>:9039`；后端 `9040` 端口可用于调试，不再要求前端页面直连。
如果确实希望浏览器直连后端，请在构建前端镜像时设置
`NEXT_PUBLIC_API_BASE_URL=http://<服务器公网 IP>:9040`，并确保安全组/防火墙/CORS 已允许该访问。

Docker 后端默认读取镜像内的 `backend/ancient_calculus.db`。如需重新导入数据，请先运行
`python scripts/import_to_db.py --reset` 生成该数据库，再重新构建后端镜像。

---

## 10. API 列表
所有接口均基于 RESTful 风格挂载于 `/api` 路由组下：
- `GET /api/summary`：获取数据库宏观统计与图表聚合数据。
- `GET /api/samples`：分页获取所有样品列表（支持跨字段组合查询）。
- `GET /api/samples/{sample_id}`：获取单个样品的历史和考古属性。
- `GET /api/samples/{sample_id}/taxa`：查询单个样品内相对丰度排名前 N 的微生物（支持按界门纲目科属种过滤）。
- `GET /api/taxa/search?q={name}`：按名称模糊匹配并搜索分类单元。
- `GET /api/taxa/top`：在大范围样品集合内（如唐代所有的农业人群），挖掘总体平均丰度最高的 Top 微生物群落。
- `GET /api/taxa/{taxid}/distribution`：透视某一种微生物在不同朝代/省份/大区间的分布数据，并携带均值、极值等信息。
- `POST /api/ai/query`：接收自然语言查询，返回基于意图解析的查询计划（Query Plan）。

## 11. 前端页面列表
- **Dashboard (`/`)**: 宏观统计大盘，全方面感知数据库中的数据结构，附带快速探索入口。
- **Samples (`/samples`)**: 支持多条件联查的综合样品浏览器。
- **Sample Detail (`/samples/[sample_id]`)**: 特定样品的详细档案与微生物组成图谱（柱状图交互）。
- **Taxa Explorer (`/taxa`)**: 跨组宏基因组群落探索页面，用于找寻不同人群组合中的优势菌。
- **Taxon Distribution (`/taxa/distribution`)**: 动态交叉透视分析工具，可三步查明任意 Taxon 的跨维度富集差异。
- **AI Query MVP (`/ai-query`)**: 自然语言处理中心（当前处于占位演示阶段）。

---

## 12. 后续扩展计划
EAAM 项目具有极高的扩展性，未来计划支持以下增强功能：
1. **Function Abundance（功能基因丰度）**：在现有物种丰度体系外，增加对古代结石宏基因组的功能潜力分析。
2. **通用的生化注释库**：支持整合 KEGG, eggNOG, HUMAnN 等国际通用数据库的数据比对结果和通路映射。
3. **Map Visualization（地图可视化）**：由于具备 `latitude/longitude` 字段，后续版本将集成 GeoJSON 将样品在地图上进行空间投影分析。
4. **Timeline Visualization（时间轴可视化）**：依托 `estimated_year` 进行时间序列维度的滑动趋势图展示。
5. **DeepSeek AI Query**：接入真正的 DeepSeek API 以替代现有的简单规则引擎，使 AI 完全具备生成任意复杂交叉查询和自动生信知识解读的能力。

---

## 13. 常见问题 (FAQ)

### `sample_id` 在 Meta 表和 Kraken2 宽表中不一致怎么办？
**答：** 这是一个极其常见的问题。由于测序上下机的批次原因，生信人员交付的原始 Kraken2 数据列名可能带有后缀（如 `GX_Tang_1_S1_L001_all`）。`convert_kraken2_to_long.py` 的作用是从前缀提取匹配名称，你需要根据具体情况微调 `convert_kraken2_to_long.py` 中的正则表达式和提取逻辑，以确保最后输出长表时的 ID 能够命中 `samples.csv` 中的 `sample_id`。

### 为什么某个样品所有物种的 relative_abundance 总和加起来不等于 1（或 100%）？
**答：**
1. 请检查计算相对丰度时的分母选取。目前系统默认以该样品在 `root` 节点的 reads_all 数值作为总体分母。
2. 有一部分 reads 被标记为 `unclassified`，如果你在下游筛选时剔除了 `Unclassified`，物种层面的累加值自然不会达到 100%。

### Kraken2 表格中 `_all` 和 `_lvl` 的核心区别是什么？
**答：**
- **`_all`（Clade reads）**：指该片段不仅匹配了当前节点，还可能匹配到了该节点的**任何子孙节点**。因此对于门、纲、目这些上级分类单元，`_all` 丰度总是显著高于 `_lvl`。我们在本项目图表中默认呈现 `relative_abundance_all`。
- **`_lvl`（Taxon reads）**：指该片段被 Kraken2 算法**严格判定并止步于**当前的层级，无法进一步细分到更具体的子节点。对于底层的种级（Species），`_all` 与 `_lvl` 往往相等。
