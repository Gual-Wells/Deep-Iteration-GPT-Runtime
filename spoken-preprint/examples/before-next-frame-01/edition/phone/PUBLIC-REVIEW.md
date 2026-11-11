# Before the Next Frame / 下一帧之前 · 处境与表达回看

这些资料帮助回到真实原句和往返；它们不记录听者已经掌握了什么。

## 面试问到代码改动，还没想清楚 API 的含义怎样先开口

此时要做的事：拿出具体改动，把做过的事、动机和待验证假设分开。

难处：回答要同时说明具体修改与尚未核查的语义，不能把节省分配的动机说成已经测得的收益；公开记录没有证明Nora曾组织不出答案。

### 回到原来的往返

**Sam**

> Before we run anything, walk me through one captured frame—from the native output to its entry in this history. My first suspicion is that a result is getting attached to the wrong frame, but I haven’t seen enough to tell. Can you show me the bit you changed when you removed the copy?

**Nora**

> Let me pull up the exact lines. I used to copy the output into a new float array for the history entry; the patch keeps the returned Tensor instead. I wanted to avoid that allocation, but I haven't checked what that Tensor actually owns.

**Nora**

> Here: I add A's wrapper to history, run B on the same module, then read both wrappers later when I render the entries. I was treating that wrapper like a saved result, but the scores might still point at something the next call reuses. Could we read A immediately, run B, and then read the retained A again?

**Sam**

> Yes—let’s check that. Keep the frame IDs and raw scores in the log, not just the displayed tags, and make A’s first read an independent value snapshot so our baseline can’t change too. Can you put the native reference for each frame beside those reads?

这段实际发生的变化：Nora拿出旧/新处理方式并公开承认ownership未查，提出检查；Sam接受提议，但加上独立快照和逐帧reference，尚未产生测试结果。

### 措辞与使用条件

**Let me pull up the exact lines.**

这里的意思：让我先调出具体代码行。

表达作用：先做一个有用的小步骤，为解释取得共同对象。

使用条件：对方问的确实是可拿出的改动；不是承诺马上知道所有答案。

语域：具体技术面谈中的口语；随真实问题调整

频率依据：未做语料频率/CEFR统计；这里只确认本册实际使用。

回看作者的变式，非角色原句：Let me show you the change first.

编辑作者拟句，非角色原话。把动作改为先展示改动，省略是否调出文件的细节。

**I was treating that wrapper like a saved result**

这里的意思：我原先把那个包装对象当成保存下来的结果。

表达作用：把正在重新考虑的原理解说清，而非只抛一个结论。

使用条件：后面but/might引出怀疑；过去进行时本身不证明当时理解错误。

语域：具体技术面谈中的口语；随真实问题调整

频率依据：未做语料频率/CEFR统计；这里只确认本册实际使用。

回看作者的变式，非角色原句：I kept the object. I’m not sure it keeps the old values.

编辑作者拟句，非角色原话。用两个短句分别说操作与未知；不假称已经证明原因。

原句出处：before-next-frame-01 / show-change / e-864b5396e75a46a7, e-7ea5c40f96cb4efb, e-ba788d06a0874666, e-af24a393cdfa41a7

片段 SHA256：0a100a9aa3aa6f8e8123aae828499e08e1b6b1a029f67dbf87fa06a187244ee3

## 测试出现变化，怎样说明看到的现象和下一步而不过度下结论

此时要做的事：区分当时的独立数值、后来读取的对象，以及新公布的产品需要。

难处：A这条历史记录的帧标识仍在，后来读到的分数却变了；看到旧读数发生变化，也不等于应该把整份输出留在历史中。

### 回到原来的往返

**Nora · 动作**

> I submit one sequential A-then-B replay to the console: run A on the live module, copy its scores into an independent array labelled A, retain its Tensor wrapper, run B on that same module, copy B's immediate scores into an independent array labelled B, then read and copy the retained A wrapper's scores again. I request frame IDs on every read and put the saved references A=[2,0,-1] and B=[-1,2,0] beside the corresponding entries.

**公开观察**

> The console completes one sequential replay on the same module. Its log shows: A | immediate independent snapshot before B | [2,0,-1] | saved A reference [2,0,-1]; B | immediate independent snapshot after B | [-1,2,0] | saved B reference [-1,2,0]; A | retained A wrapper read after B | [-1,2,0] | saved A reference [2,0,-1]. One replay slot remains.

**Nora**

> Oh—that retained A has B's scores now. Keeping the Tensor hasn't preserved A's result in this run. I'd restore the independent copy immediately after each call and use the last replay to check both history entries after B.

**Sam**

> That log makes a frame mix-up less convincing; the retained A read has actually changed. Before you spend the last replay, there’s a requirement I haven’t given you: history only needs each frame’s label and raw top score. Does that change what you’d save? Talk me through the change you’d put up for review and what the last replay would establish.

**Nora**

> Yes—that's smaller than putting the whole array back. For review I'd replace the history Tensor with a frame ID, label and float score, taking the maximum and copying those values before the next inference. I'd still need to check whether reading the scores through this wrapper requires a temporary array. Then I'd use the last replay to render both entries after B and compare them with the references: different labels, both raw scores 2. If that passes, we've checked this two-frame history case; we haven't measured a speedup.

这段实际发生的变化：虚构replay后旧A读成B，Nora先提恢复复制；Sam给出此前没说的label/top-score需求，她改为小记录并保留读取API是否需临时数组的未知。

### 措辞与使用条件

**Keeping the Tensor hasn't preserved A's result in this run.**

这里的意思：这一次保留Tensor对象，没有保住A当时的结果。

表达作用：用对象与具体观察限定结论。

使用条件：in this run限制本次复现，不概括所有Tensor/后端；该书数值为明确虚构。

语域：具体技术面谈中的口语；随真实问题调整

频率依据：未做语料频率/CEFR统计；这里只确认本册实际使用。

回看作者的变式，非角色原句：The old A now shows B’s scores.

编辑作者拟句，非角色原话。更短地描述现象，没有替代所有权解释。

**makes a frame mix-up less convincing**

这里的意思：使“帧关联弄混”这个解释不那么站得住。

表达作用：根据新证据降低一种解释的说服力。

使用条件：less convincing不是绝对排除；需要原来的怀疑与这次log。

语域：具体技术面谈中的口语；随真实问题调整

频率依据：未做语料频率/CEFR统计；这里只确认本册实际使用。

回看作者的变式，非角色原句：That makes me less sure it’s a frame mix-up.

编辑作者拟句，非角色原话。更突出说话者判断变化，也仍不宣称完全排除。

**I'd still need to check whether reading the scores through this wrapper requires a temporary array.**

这里的意思：我仍要查，通过这个包装对象读分数是否还需要临时数组。

表达作用：把还没想清的实现问题留成一个具体可追问点。

使用条件：产品只留label/top score，不自动说明读取时没有数组；原作最后仍采用临时数组。

语域：技术面谈

频率依据：未做语料频率统计；本册实际使用。

回看作者的变式，非角色原句：We don't need the whole array in the history. I still need to check how to read the values.

编辑示范，非Nora原句。先复述保留需求，再保留读取方法未知，不声称已消除临时数组。

回看作者的变式，非角色原句：Can I work through that with the code in front of me?

编辑示范，非新人物回合。请求借具体代码逐步梳理；没有替此请求编造对方接受或测试成功。

原句出处：before-next-frame-01 / what-the-test-shows / e-314258bc217b4875, e-968b587662dd4831, e-9010dbf81d5e40ee, e-4ecac46f2bf64859, e-35b39e4ee8f348f2

片段 SHA256：0b29ed75ec9a32026e445bb674204427a1907883cc7985245cf100b97c869505

## 做出正确性修复，怎样承认代价并说明个人贡献而不把项目说没价值

此时要做的事：把已展示的fixture行为、待做的真实集成、个人贡献与性能证据分别交代。

难处：原先想去掉allocation，眼下修复却保留临时数组；“我做的”又容易越界成整个模型/后端都是本人完成。

### 回到原来的往返

**Sam**

> Show me the edit and the rendering path, then run that version through the last replay. I want to see whether the code actually does what you’ve just described, especially what the history entry holds by the time B starts.

**Nora · 动作**

> I write a replacement for the fixture in explicit pseudocode: `saveFrame(id, input) { scores = independentFloatArrayImmediatelyAfter(runSameMethod(input)); k = argmax(scores); history.add(HistoryEntry(copyValue(id), copyValue(labelFor(k)), floatValue(scores[k]))); } saveFrame(A, ownedInputA); saveFrame(B, ownedInputB); later { for (entry in history) render(entry.frameId, entry.label, entry.rawTopScore); }`. I use the old independent-array conversion for this version, with the array local to saveFrame and only copied ID, label and score values retained in history. I submit that edit and rendering path for the final A-then-B replay, requesting the immediate score snapshots and the two delayed rendered records alongside the unchanged references.

**公开观察**

> The final fixture replay displays the submitted pseudocode's immediate snapshots: A=[2,0,-1], beside saved A reference [2,0,-1]; B=[-1,2,0], beside saved B reference [-1,2,0]. The delayed render after B shows two saved records: A | label0 | raw top score 2; B | label1 | raw top score 2. No replay slots remain.

**Nora**

> Okay, that's a relief—A is still label0 after B, and both saved scores are 2. That's the behavior I'd carry into the Android adapter, with this A-then-B sequence kept as a regression test. I'd leave the temporary array in for that fix and profile it before trying to remove it again.

**Sam**

> I’d want the Android diff and that regression test for review. Before we wrap up, which parts of this integration did you build yourself, and what did you reuse from the runner? I want to be clear about what I’m assessing as your work.

**Nora**

> I built the Android frame capture, the code that calls the native runtime, and the frame/result history and display. Model execution came from the existing runner/runtime; I didn't write the backend or kernels. My teammate selected and trained the classifier. The Tensor-retention patch was mine too, including the assumption that the wrapper would preserve an old result, so that's my integration code to correct.

**Sam**

> I’ve seen enough here to recommend a focused technical follow-up. For that review, I’d want the Android diff and the A-then-B regression test you described; the adapter fix itself is still unverified. Let’s leave it there for today.

这段实际发生的变化：最后一次虚构fixture保留了两条正确标签/分数，但示意代码恢复了临时数组；Nora说明自己的集成及他人贡献，Sam仅推荐follow-up。公开片段没有展示实际Android修复或运行验证，不能把待review缩成唯一剩余步骤。

### 措辞与使用条件

**I'd leave the temporary array in for that fix and profile it before trying to remove it again.**

这里的意思：针对这个修复，我会先保留临时数组，先做性能剖析，再尝试去掉。

表达作用：把眼前正确性修复与以后优化分开，同时保留下一步。

使用条件：I’d是当前建议/打算，不等于已经profile；两帧fixture也不是实机性能结果。

语域：具体技术面谈中的口语；随真实问题调整

频率依据：未做语料频率/CEFR统计；这里只确认本册实际使用。

回看作者的变式，非角色原句：I can keep this for the fix. I haven’t measured its cost yet.

编辑作者拟句，非角色原话。短句明确范围与未知；haven’t measured … yet说明截至现在还未测，当前仍缺这份证据；yet本身不承诺以后一定完成，不能当通用台词冒充本人真实项目。

**I didn't write the backend or kernels.**

这里的意思：后端和算子内核不是我写的。

表达作用：在已说明自己做的部分后划贡献边界。

使用条件：前文确实有本人的capture/integration/history/display；不能用这句推断本人不懂内核。

语域：具体技术面谈中的口语；随真实问题调整

频率依据：未做语料频率/CEFR统计；这里只确认本册实际使用。

回看作者的变式，非角色原句：I built the integration. I reused the runtime.

编辑作者拟句，非角色原话。更概括地分开个人实现与复用，具体职责仍需实际材料支持。

原句出处：before-next-frame-01 / repair-is-not-speedup / e-1aca05bcb26244da, e-58592dc4d28e475c, e-ee3e7b10beda49f1, e-ea14a6fd83e6429c, e-1e07794c2f9a479a, e-e5cf365c807542b2, e-03e9a56e1dd74af9

片段 SHA256：e55b48e956bdee049c6c32f60df0675f793693f0186b3c8851c8ca651979a699
