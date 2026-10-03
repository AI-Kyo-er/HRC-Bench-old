"""Mechanism tests: history dependence, private information boundary, physical evaluation."""
import unittest
from dataclasses import asdict

from hrc_pilot.evaluation import evaluate
from hrc_pilot.partner import ResponsivePartner
from hrc_pilot.policies import CoordinationPolicy
from hrc_pilot.protocol import Message, Observation
from hrc_pilot.scenarios import SCENARIOS


def observation(messages):
    return Observation(objects={"red": (0.65, 0.27, 0.82), "blue": (0.35, -0.08, 0.82)},
        regions={"tray_red": (0.62, -0.28, 0.82), "tray_blue": (0.42, -0.32, 0.82)},
        messages=tuple(messages), robot_ee=(0.3, 0, 1.1), human_position=(0.5, 0.9, 0),
        held_by_human=(), completed_skills=())


class PilotMechanismTests(unittest.TestCase):
    def test_same_scene_and_intervention_different_history_changes_action(self):
        outputs = []
        for name in ("history_keep", "history_pack"):
            partner = ResponsivePartner(SCENARIOS[name])
            obs = observation(partner.initial_messages() + [partner.movement_message()])
            outputs.append(CoordinationPolicy().act(obs).object_id)
        self.assertEqual(outputs, ["blue", "red"])

    def test_update_is_not_revealed_before_public_evidence(self):
        partner = ResponsivePartner(SCENARIOS["information_update"])
        messages = partner.initial_messages()
        policy = CoordinationPolicy()
        self.assertEqual(policy.act(observation(messages)).object_id, "red")
        partner.on_visible_approach("red", 0.2)
        self.assertEqual(partner.understanding, "keep")
        self.assertEqual(policy.act(observation(messages)).object_id, "red")
        messages.append(partner.correction_message())
        self.assertEqual(policy.act(observation(messages)).kind, "acknowledge")
        self.assertEqual(policy.act(observation(messages)).object_id, "blue")

    def test_partner_refusal_changes_allocation(self):
        partner = ResponsivePartner(SCENARIOS["partner_unavailable"])
        messages = partner.initial_messages()
        policy = CoordinationPolicy()
        self.assertEqual(policy.act(observation(messages)).kind, "request_help")
        reply, accepted = partner.on_public_request("blue", ())
        self.assertFalse(accepted)
        messages += [reply]
        self.assertEqual(policy.act(observation(messages)).kind, "acknowledge")
        self.assertEqual(policy.act(observation(messages)).kind, "transfer")

    def test_observation_has_no_private_scenario_or_goal(self):
        serialized = asdict(observation([]))
        self.assertFalse({"scenario", "final_red", "human_available", "understanding", "expected_goal"} & serialized.keys())

    def test_evaluator_checks_physical_outcome_and_not_finish_claim(self):
        obs = observation([])
        result = evaluate(SCENARIOS["history_keep"], obs.objects, obs.regions, [], True)
        self.assertFalse(result["task_success"])
        positions = dict(obs.objects, blue=obs.regions["tray_blue"])
        self.assertTrue(evaluate(SCENARIOS["history_keep"], positions, obs.regions, [], True)["task_success"])
        positions["red"] = obs.regions["tray_red"]
        self.assertFalse(evaluate(SCENARIOS["history_keep"], positions, obs.regions, [], True)["task_success"])

    def test_airborne_or_off_table_objects_do_not_satisfy_task(self):
        obs = observation([])
        positions = dict(obs.objects, blue=(0.42, -0.32, 2.0))
        self.assertFalse(evaluate(SCENARIOS["history_keep"], positions, obs.regions, [], True)["task_success"])
        positions = dict(obs.objects, blue=obs.regions["tray_blue"], red=(5, 5, 0.82))
        self.assertFalse(evaluate(SCENARIOS["history_keep"], positions, obs.regions, [], True)["task_success"])


if __name__ == "__main__":
    unittest.main()
