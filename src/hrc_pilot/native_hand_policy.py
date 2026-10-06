"""对生成式伙伴公开实际抓/放接口；目标和当前动作仍由模型选择。"""
import json

from .continuous import HumanCommand
from .native_action_validation import command_feedback
from .native_autonomous_human import AutonomousNativeHuman
from .native_contact_human import NativeQwenHuman


class ArticulatedSkills:
    def _system_prompt(self):
        text=super()._system_prompt()
        text=text.replace('只支持push、observe、yield、away、return；push通过指尖实际受力推物，不支持抓持。',
                          '实际接触手支持push、grasp、place、release、observe、yield、away、return。')
        text=text.replace('支持的意图为push、observe、yield、away、return。','支持的意图为push、grasp、place、release、observe、yield、away、return。')
        text=text.replace('本执行器不支持抓持，不输出approach或carry。','本执行器通过真实双指摩擦抓持；使用grasp/place，不输出approach或carry。')
        return text+('grasp选择可见object_id，接触手接近、闭指、真实抬起，失败会反馈motor_failure；发出grasp不代表握住。'
                     '只有测得object_measured_in_hand为所选对象时，place才可搬运到destination并真实释放。'
                     'grasp尚在运行时，可再次选择grasp继续；observe暂停运动但保留夹指，不替你自动执行后续计划。'
                     'release明确打开手；不能拿着物体同时推另一个物体，先决定是否放下。'
                     '高台cookies_shelf的支撑面比桌面高8cm，水平push不会把物体抬到台面，实际抓放需要你自己选择。'
                     'contact_model和双指接触来自执行反馈，不是评分器给出的目标是否完成。')

    def _prompt(self,observation):
        value=json.loads(super()._prompt(observation).split('\n',1)[1])
        value['action_interface']['intents']=['push','grasp','place','release','observe','yield','away','return']
        return '根据实际接触手接口、自身意图及当前感知，自主选择下一动作：\n'+json.dumps(value,ensure_ascii=False,separators=(',',':'))

    def _native_command(self,value,observation):
        intent=value.get('intent')
        if intent=='grasp' and value.get('object_id') in observation.objects:
            return HumanCommand('grasp',value['object_id'],value.get('destination'),speed_mps=.20)
        if intent=='place' and value.get('object_id') in observation.objects and value.get('destination') in observation.regions:
            return HumanCommand('place',value['object_id'],value['destination'],speed_mps=.20)
        if intent=='release':return HumanCommand('release')
        return super()._native_command(value,observation)

    def _validated_command(self,value,observation):
        command=self._native_command(value,observation)
        supported=['push','grasp','place','release','observe','yield','away','return']
        self.last_command_feedback=command_feedback(value,command,observation.objects,observation.regions,valid_intents=supported)
        held=observation.human_execution.get('object_measured_in_hand')
        error=('requested_object_not_in_measured_hand' if value.get('intent')=='place' and held!=value.get('object_id')
               else 'hand_occupied_requires_explicit_release' if value.get('intent')=='push' and held else None)
        if error:
            command=HumanCommand('observe');self.last_command_feedback['status']='rejected'
            self.last_command_feedback['errors'].append(error)
            self.last_command_feedback['accepted']={'intent':'observe','object_id':None,'destination':None}
        return command


class ArticulatedAutonomousHuman(ArticulatedSkills,AutonomousNativeHuman):pass
class ArticulatedAssignedHuman(ArticulatedSkills,NativeQwenHuman):pass
