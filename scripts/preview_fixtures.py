"""Isolated UI fixtures. Run with .venv/bin/python scripts/preview_fixtures.py.
No real media processing or model calls. Restart to restore fixture content.
"""
import json
import os
from pathlib import Path
import shutil
import sys
from datetime import datetime, timedelta

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / '.ui-fixtures'
sys.path.insert(0, str(ROOT))
os.environ['VIDEO_DEVOUR_DATA_DIR'] = str(DATA)

def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2))

def seed():
    DATA.mkdir(exist_ok=True)
    output = DATA / 'output'
    output.mkdir(exist_ok=True)
    tasks = {}
    topics = [
        ('空间里的设计智慧：从自然光、材料到真实生活动线的完整设计研究', ['留白与注意力', '自然光与时间', '材料与触感', '动线与可达性', '声学与安静', '色彩与情绪', '模块化家具', '预算与取舍', '原型验证', '长期维护', '用户访谈', '设计复盘']),
        ('机器学习入门：数据泄漏、交叉验证与模型评估', ['训练与验证', '数据泄漏', '混淆矩阵', '交叉验证', '公平性', '部署监控']),
        ('城市生态与可持续交通', ['步行网络', '公共交通', '雨水花园', '热岛效应', '社区参与']),
        ('专注', ['环境整理', '时间规划']),
        ('复杂系统中的因果推断与实验设计：当相关性无法解释真实世界', ['混杂变量', '随机实验', '自然实验', '敏感性分析', '外部有效性']),
        ('海洋观察日志 🌊：珊瑚、洋流与生物多样性', ['珊瑚共生', '洋流输运', '观测误差', '保护策略']),
        ('产品复盘：需求、交付与团队协作', ['问题定义', '方案比较', '验收标准', '回顾改进']),
        ('一杯咖啡的风味实验', ['萃取比例', '水温控制', '研磨尺度', '感官记录']),
    ]
    for i, (title, chapters) in enumerate(topics):
        for version in range(1, 4 if i == 0 else 2):
            tid = f'fixture-{i+1:02}-{version}'
            stamp = datetime.now() - timedelta(days=i, hours=3-version)
            folder = output / f'frames_{tid}_{stamp:%Y%m%d_%H%M%S}'
            # Stable path allows repeat runs without accumulating duplicate versions.
            old = list(output.glob(f'frames_{tid}_*'))
            if old: folder = old[0]
            folder.mkdir(exist_ok=True)
            tasks[tid] = dict(task_id=tid, filename=f'[测试] {title}', status='completed', progress=100,
                created_at=stamp.isoformat(), video_key=f'fixture-video-{i+1:02}', education_level='自由学习', message='测试数据 · 已完成')
            image = ROOT / 'frontend/public/coast' / ('reading.png' if i%2 else 'sculpture.png')
            shutil.copyfile(image, folder/'cover.png')
            sections=[]
            for j,c in enumerate(chapters):
                sections.append(f'## {c}\n\n这是用于检查「{title}」第 {j+1} 个章节的合成材料，不代表真实视频结论。V{version} 在本章增加了可验证的观察与反例。\n\n'
                    f'### 关键观察与边界\n\n{c}需要结合情境理解：先记录事实，再提出解释，最后设计一个可以重复的对照。单次结果不能直接替代长期趋势。\n\n'
                    '> 讲者 A（03:20）：先把问题描述清楚，再讨论方案。\n>\n> 讲者 B（03:45）：如果条件改变，结论是否仍成立？\n\n'
                    '| 方案 | 观察指标 | 优点 | 限制 |\n| --- | --- | --- | --- |\n| 基线 | 42% | 易于复现 | 情境有限 |\n| 改进 | 68% | 降低干扰 | 需要额外验证 |\n\n'
                    '- 明确目标和使用场景。\n- 记录失败条件与不确定性。\n- 对比方案后再总结。\n\n'
                    '### 实践与反思\n\n1. 选择一个真实场景。\n2. 保持其他变量不变。\n3. 记录结果并复盘。\n\n')
            base=f'# {title}\n\n测试样本 · 第 {version} 版 · 包含长文本、目录、表格和多层章节。\n\n'
            detailed=base+'\n'.join(sections)
            outline=base+'![测试封面](cover.png)\n\n'+'\n'.join(sections)
            if i==1: detailed+='\n## 代码示例\n\n```python\nfor fold in range(5):\n    train, valid = split(data, fold)\n    evaluate(train, valid)\n```\n'
            content={'detailed_outline.md':outline,'final_report.md':detailed,'detailed_report.md':detailed+'\n## 访谈原文补充\n\n'+''.join(sections),
                'quantum_read.md':base+'## 30 秒速读\n\n'+ '\n'.join(f'- **{c}**：观察、比较、验证。' for c in chapters),
                'wechat_article.md':base+'## 从一个日常问题开始\n\n一个好的问题，往往比一个快速的答案更有价值。\n\n'+''.join(sections[:3]),
                'xiaohongshu_article.md':base+'## 我的实践清单 ✨\n\n'+ '\n'.join(f'- [ ] {c}：今天尝试一次小实验。' for c in chapters)+'\n\n#学习笔记 #设计研究 #测试样本'}
            for name,body in content.items():
                (folder/name).write_text(body)
                os.utime(folder/name,(stamp.timestamp(),stamp.timestamp()))
            mind='# '+title+'\n'+''.join(f'## {c}\n### 核心观点\n- 观察事实\n- 对照实验\n### 行动建议\n- 记录边界\n- 复盘验证\n' for c in chapters)
            (folder/'mindmap.html').write_text('<script type="text/template">'+mind+'</script>')
            nodes=[{'name':title,'desc':'综合主题与多章节关联'}]+[{'name':c,'desc':f'{c}的事实、解释、证据和适用边界。'} for c in chapters]
            links=[{'source':title,'target':c,'relation':'包含'} for c in chapters]+[{'source':chapters[j],'target':chapters[(j+1)%len(chapters)],'relation':'相互影响'} for j in range(len(chapters))]
            (folder/'knowledge_graph.html').write_text('const graphData = '+json.dumps({'nodes':nodes,'links':links},ensure_ascii=False)+'; const chart = null;')
            questions=[]
            for q in range(12):
                kind=['single','multiple','boolean'][q%3]
                options=['先记录事实与边界','直接推广单次结果','进行对照验证','忽略不一致数据'] if kind!='boolean' else ['正确','错误']
                answer=[0,2] if kind=='multiple' else [0]
                questions.append(dict(id=f'q{q+1}',type=kind,chapter=chapters[q%len(chapters)],question=f'在「{chapters[q%len(chapters)]}」的实践中，'+('应该先记录事实与适用边界。' if kind=='boolean' else '哪些做法有助于得到可靠结论？' if kind=='multiple' else '首先应该采取哪项行动？'),options=options,answer=answer,explanation='先记录事实与边界，再开展对照验证；避免将单次观察直接推广到所有场景。'))
            write_json(folder/'quiz.json',dict(version=1,title=title,question_count=12,education_level='自由学习',generated_at=stamp.isoformat(),questions=questions))
            write_json(folder/'fixture_asr_result.json',[{'video_path':title+'.mp4','transcript':[{'end_time':4200 if i==0 else 900+i*157}]}])
            write_json(folder/'timing_report.json',{'summary':{'total_elapsed':156,'phases':[{'name':n,'total':v,'duration':v,'count':1} for n,v in [('获取视频',12),('语音识别',48),('关键画面',32),('内容生成',64)]]}})
            (folder/'timing_summary.txt').write_text('测试耗时：总计 156 秒。获取视频 12 秒，语音识别 48 秒，关键画面 32 秒，内容生成 64 秒。')
    for i,(status,progress,msg) in enumerate([('processing',12,'正在读取视频信息'),('processing',68,'正在整理第 8 / 12 章'),('processing',95,'正在生成学习内容'),('pending',0,'等待处理'),('failed',0,'网络连接中断，请重试'),('failed',0,'语音识别服务超时'),('failed',0,'视频文件格式无法解析')]):
        tid=f'fixture-state-{i}'
        tasks[tid]=dict(task_id=tid,filename=f'[测试] {msg}',status=status,progress=progress,message=msg,error=msg if status=='failed' else '',created_at=datetime.now().isoformat(),stage='error' if status=='failed' else 'processing')
        (output/f'frames_{tid}_20260916_120000').mkdir(exist_ok=True)
    write_json(DATA/'tasks.json',tasks)
    return tasks

if __name__=='__main__':
    tasks=json.loads((DATA/'tasks.json').read_text()) if '--keep-data' in sys.argv and (DATA/'tasks.json').exists() else seed()
    from backend.api import main
    # These states intentionally have no processing worker; restore after startup recovery.
    main.processing_tasks.update(tasks)
    from fastapi.responses import JSONResponse
    @main.app.middleware('http')
    async def fixture_boundary(request,call_next):
        if request.method=='POST' and not request.url.path.endswith('/quiz/submit') and not (request.url.path.startswith('/api/editor/') and request.url.path.endswith('/images')):
            return JSONResponse({'detail':'独立测试环境：此操作需要真实处理服务。当前样本已预生成，可直接查看；不会调用外部模型。'},status_code=409)
        return await call_next(request)
    import uvicorn
    print('UI fixtures: http://127.0.0.1:8001 — 8 videos, 10 completed runs, 7 status cases')
    uvicorn.run(main.app,host='127.0.0.1',port=8001)
