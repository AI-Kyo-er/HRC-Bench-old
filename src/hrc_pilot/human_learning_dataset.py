"""以相同stem匹配真实接触示范的输入与标签，不使用配对manifest。"""
import json
from pathlib import Path


class HumanLearningDataset:
    def __init__(self,root,split):
        self.root=Path(root);self.paths=[];self.diagnostic_episodes=set()
        for path in sorted((self.root/'samples'/split).glob('*.source.json')):
            source=json.loads(path.read_text());episode=path.name.removesuffix('.source.json').split('__step',1)[0]
            assert source['episode_id']==episode
            metric=json.loads((self.root/'episodes'/episode/'metrics.json').read_text())
            if set(metric['terminal_released_stable_targets'])!={t['object_id'] for t in metric['targets']}:
                self.diagnostic_episodes.add(episode);continue
            self.paths.append(path)
        if not self.paths:raise ValueError('没有完成全部真实释放稳定目标的示范')

    def __len__(self):return len(self.paths)

    def __getitem__(self,index):
        path=self.paths[index];stem=path.name.removesuffix('.source.json')
        source=json.loads(path.read_text());target=json.loads((path.parent/(stem+'.target.json')).read_text())
        # 训练首次由NN选择意图的接口，物理测量及教师标签原样保留。
        if source['time_s']==0:
            title,value=source['public_input'].split('\n',1);public=json.loads(value)
            public['your_previous_personal_targets']=[];public['your_long_term_intention']=''
            source['public_input']=title+'\n'+json.dumps(public,ensure_ascii=False,separators=(',',':'))
        return source,target
