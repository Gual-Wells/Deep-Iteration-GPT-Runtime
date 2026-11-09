# 独立探索B：无序账本的引用基数与净额守恒

已读四项规范及原件/种子；本次只在task2继续形成领域认识。未改output或输入。

可复核试作：run/explore_b_relational_probe.py；运行 python -B 此文件。
该试作是关系优先的研究模型，并非正式交付budget.py。

## 材料提出的真正问题

金额加法是局部可交换的，退款归属却依赖完整账本中的expense关系。
同一id出现两个expense即不唯一，金额0也没有消除记录存在性的资格。
这个基数语义使三键汇总结果不是可独立合并的充分统计量。

## 已运行反例

1. expense(x,100,food)+refund(x,30) -> food=70, unassigned=0。
   再加入expense(x,0,food) -> food=100, unassigned=-30。
   总净额仍70；归属改变。不能先去零、按id覆盖或合并同分类同id记录。
2. expense候选[food,unknown,food] -> unassigned=50，不是food=50。
   先按候选本身去重；未知候选也是使其歧义的竞争项。
3. expense(x,10,food)+refund(x,30) -> food=-20。
   unassigned也允许负数，因此它是有符号金额桶，不是只增不减的错误计数器。
4. refund无自己的候选时，种子在同一对记录的两个排列得到不同结果；关系模型不变。
5. transfer金额True/False/-1/1.0均应被拒绝；先验证才能决定不计金额。
   同id的transfer/refund不增加expense匹配基数；转账7计数为1。

## 更强的不可合并证明

前缀A=[expense(x,100,food)]与A'=[expense(y,100,food)]拥有完全相同三键结果。
追加相同后缀B=[refund(x,30)]后，A+B=(food70,U0)，A'+B=(food100,U-30)。
因此不存在仅消费两个已最终化三键结果、便能普遍恢复整账结果的合并函数。
不能把普通“加法不满足”弱化成改一次加法就能解决的问题；信息已在最终化时丢失。

## 可落实的方法

先验证所有金额；建立仅含expense的id->记录多重关系；再对各行做正负桶累加。
唯一性按记录数而非候选分类数，退款自己的候选绝不进入推导。
核对守恒式：sum(used)+unassigned = sum(expense.amount)-sum(refund.amount)。
该式对所有排列和金额0仍成立；不声称守恒独自证明归属正确。

## 下一次值得继续研究

若正式实现采用轻量id索引，审查是否用覆盖、按分类去重或去零偷换了基数。
更深的问题是：保持正确可合并性最少需要保存什么？一个候选是每id三态
(absent / singleton(category或不可归类) / multiple)，连同退款按目标id的金额和。
absent与singleton(不可归类)必须区分，因为未来加入唯一可归类expense会分别产生
singleton与multiple。multiple可吸收后续expense，但须保留正向金额桶贡献。
此候选尚未实现或验证，不把它当成正式成果或完成D。
