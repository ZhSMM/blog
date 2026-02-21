# CSS3入门

#### 基础选择器

| 选择器类型         | 语法示例                 | 描述与作用                                                   | 权重值 (Specificity)            | 代码示例与解释                                               |
| ------------------ | ------------------------ | ------------------------------------------------------------ | ------------------------------- | ------------------------------------------------------------ |
| **通配选择器**     | `*`                      | 匹配文档中的**所有元素**。常用于重置默认样式（如 `margin`, `padding`）。 | **0,0,0,0**                     | `* { margin: 0; padding: 0; box-sizing: border-box; }`<br />*解释：将所有元素的边距、内边距设为0，并设置为边框盒模型。* |
| **元素选择器**     | `div`、`p`、`h1`         | 根据**HTML标签名**来选择元素。也称为“标签选择器”。           | **0,0,0,1**                     | `p { color: #333; line-height: 1.6; }` <br />*解释：选择所有 `<p>`段落元素，并设置其文字颜色和行高。* |
| **类选择器**       | `.className`             | 根据元素的 `class`属性值来选择。一个元素可以有多个类，一个类也可用于多个元素。**最常用的选择器之一**。 | **0,0,1,0**                     | `<div class="box active"></div>` `.box { border: 1px solid #ccc; }` `.active { background-color: yellow; }` <br />*解释：`.box`选中所有 `class`包含 `box`的元素；`.active`会为元素添加黄色背景。* |
| **ID 选择器**      | `#idName`                | 根据元素的 `id`属性值来选择。**ID在文档中应是唯一的**。权重很高，应谨慎使用。 | **0,1,0,0**                     | `<header id="main-header"></header>` `#main-header { height: 60px; background: blue; }`<br /> *解释：选中 `id`为 `main-header`的唯一元素，并设置其样式。* |
| **属性选择器**     | `[attr]`、`[attr=value]` | 根据元素的**属性及属性值**来选择元素。非常灵活。             | **0,0,1,0**  （与类选择器同级） | 1. `[disabled] { opacity: 0.5; }` *选中所有带有 `disabled`属性的元素。* <br />2. `input[type="text"] { border-color: blue; }` *选中 `type`属性为 `text`的 `<input>`元素。*<br /> 3. `a[href^="https"]`(以...开头), `a[href$=".pdf"]`(以...结尾) 等。 |
| **后代选择器**     | `selectorA selectorB`    | （空格连接）选择 **selectorA 元素内部的所有后代** selectorB 元素。 | **权重为所有部分之和**          | `.article p { text-indent: 2em; }` <br />*解释：选中所有在 `class="article"`的元素**内部的** `<p>`元素，无论嵌套多深。* |
| **子元素选择器**   | `selectorA > selectorB`  | （大于号连接）选择 **selectorA 元素的直接子元素** selectorB。**只匹配一代**。 | **权重为所有部分之和**          | `.menu > li { border-bottom: 1px solid #eee; }` <br />*解释：只选中 `.menu`下一级的 `<li>`子元素，不会选中更深的 `<li>`。* |
| **相邻兄弟选择器** | `selectorA + selectorB`  | （加号连接）选择 **紧跟在 selectorA 之后** 的第一个同辈 selectorB 元素。 | **权重为所有部分之和**          | `h2 + p { margin-top: 0; }` <br />*解释：选中紧跟在 `<h2>`后面的第一个 `<p>`段落。* |
| **通用兄弟选择器** | `selectorA ~ selectorB`  | （波浪号连接）选择 **selectorA 之后的所有同辈** selectorB 元素。 | **权重为所有部分之和**          | `.active ~ li { color: gray; }` <br />*解释：选中所有在 `.active`类元素**之后**的同级 `<li>`元素。* |
| **群组选择器**     | `selA, selB, selC`       | （逗号连接）**同时选中**多个选择器对应的元素，并为它们应用相同的样式。 | **各自独立计算，不叠加**        | `h1, h2, .title, #main-heading { font-family: ‘Microsoft YaHei’; }` <br />*解释：将上述列出的所有标题、类、ID 的字体统一设置为微软雅黑。* |

```html

```



