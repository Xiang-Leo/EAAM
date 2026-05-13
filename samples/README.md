# EAAM 上传文件模板说明

这个目录用于给数据维护人员提供标准上传格式。正式上传前，请优先整理下面 3 个必需文件；另外 2 个可选文件用于网页跳转链接和数据集说明。

## 必需文件

1. `samples_metadata.csv`
   - 样品元数据表。
   - 所有丰度表里的样品列，都必须能在这里找到对应的 `sample_id`。
   - `sample_id` 必须完全一致，包括大小写、下划线和数字。

2. `functional_genefamilies_ko_relab_unstratified.tsv`
   - KO gene families 相对丰度矩阵。
   - 第一列固定为 `feature_id`。
   - 后面每一列都是样品 ID。

3. `functional_pathabundance_relab_stratified.tsv`
   - Pathway 相对丰度矩阵。
   - 前三列固定为 `feature_id`、`feature_name`、`stratification`。
   - 后面每一列都是样品 ID。

## 可选文件

4. `feature_links.csv`
   - 用于给样品、KO、pathway、文献 DOI 等增加网页跳转链接。

5. `dataset_manifest.csv`
   - 用于记录每次上传的数据集来源、版本、说明。

## 整理规则

- 不要出现空样品列。
- 不要出现重复样品列。
- 不要把说明行放进 TSV 数据区，例如 `Lable`、`Label` 这类行应删除或整理到 metadata 文件。
- 丰度数值建议使用 0 到 1 之间的小数。
- 缺失值建议填 `0`，不要填 `NA`、`None`、`-`。
- 经纬度可以为空，但如果填写必须是数字。
- DOI 可以只写 DOI 编号，也可以在 `feature_links.csv` 里提供 `https://doi.org/...` 跳转链接。

## 上传前自查

请确认：

- `samples_metadata.csv` 里的 `sample_id` 覆盖了所有丰度表的样品列。
- KO 表和 pathway 表中的样品列名称一致，或至少都能在 metadata 里找到。
- pathway 表中的分层信息已经拆分到 `stratification` 列。
- 文件保存为 UTF-8 编码。
