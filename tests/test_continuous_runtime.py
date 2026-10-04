"""持续运行时的机制测试。"""
import unittest
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory

from hrc_pilot.continuous import (
    AdaptivePartner,
    CONTINUOUS_SCENARIOS,
    ContinuousWorld,
    GreedyPublicPolicy,
    run_catalog,
)
from hrc_pilot.protocol import Action, Message
from hrc_pilot.benchmark import ModelPolicy, decode_action, public_observation_dict


class ContinuousRuntimeTests(unittest.TestCase):
    def test_catalog_is_composable_and_runs_without_event_script(self):
        results = run_catalog(seed=3)
        self.assertEqual(len(results), 6)
        self.assertTrue(all(result["task_success"] for result in results))
        self.assertTrue(any(result["proximity_warnings"] > 0 for result in results))

    def test_partner_reacts_to_visible_robot_occupation(self):
        scenario = CONTINUOUS_SCENARIOS["concurrent_overlay"]
        world = ContinuousWorld(scenario)
        world.reset(0)
        partner = AdaptivePartner(scenario)
        partner.reset(0)
        for message in partner.initial_messages():
            world.say(message)
        idle = partner.step(world.observe()).command
        world.start_action(Action("transfer", "blue", "tray_blue"))
        occupied = partner.step(world.observe()).command
        self.assertNotEqual(idle.intent, "yield")
        self.assertEqual(occupied.intent, "yield")

    def test_public_observation_does_not_leak_private_goals(self):
        world = ContinuousWorld(CONTINUOUS_SCENARIOS["history_reinterpretation"])
        world.reset(0)
        observation = asdict(world.observe())
        self.assertFalse({"scenario", "robot_targets", "human_targets", "human_availability", "trust"}
                         & observation.keys())

    def test_action_can_be_preempted_before_completion(self):
        world = ContinuousWorld(CONTINUOUS_SCENARIOS["relay"])
        world.reset(0)
        world.start_action(Action("transfer", "blue", "tray_blue", duration_steps=20))
        world.tick()
        world.start_action(Action("wait", duration_steps=2))
        self.assertEqual(world.interruptions, 1)
        self.assertTrue(any(event["kind"] == "robot_action_preempted" for event in world.events))

    def test_joint_action_chunk_is_accepted(self):
        world = ContinuousWorld(CONTINUOUS_SCENARIOS["relay"])
        world.reset(0)
        world.start_action(Action("joint_position", joints=tuple([0.1] * 9), duration_steps=3,
                                  control_mode="joint_position"))
        for _ in range(3):
            world.tick()
        self.assertEqual(world.robot_qpos.shape, (9,))
        self.assertGreater(float(world.robot_qpos[0]), 0.0)

    def test_generated_instances_change_layout_and_run(self):
        from hrc_pilot.continuous import generate_scenarios
        scenarios = generate_scenarios(3, seed=19)
        self.assertEqual([scenario.name for scenario in scenarios],
                         ["generated_000", "generated_001", "generated_002"])
        self.assertNotEqual(scenarios[0].objects[0].position, scenarios[1].objects[0].position)
        results = run_catalog(seed=4, scenarios=scenarios)
        self.assertTrue(all(result["task_success"] for result in results))

    def test_model_adapter_accepts_public_json_only(self):
        scenario = CONTINUOUS_SCENARIOS["relay"]
        world = ContinuousWorld(scenario)
        world.reset(0)
        for message in AdaptivePartner(scenario).initial_messages():
            world.say(message)
        observation = world.observe()
        encoded = public_observation_dict(observation)
        self.assertNotIn("human_targets", encoded)
        policy = ModelPolicy(lambda _: {"kind": "wait", "duration_steps": 2})
        policy.reset()
        self.assertEqual(policy.act(observation).kind, "wait")
        with self.assertRaises(ValueError):
            decode_action({"kind": "wait", "private_goal": "red"})

    def test_episode_writes_public_records_and_private_instance_separately(self):
        from hrc_pilot.continuous import run_continuous_episode
        scenario = CONTINUOUS_SCENARIOS["relay"]
        with TemporaryDirectory() as directory:
            output = Path(directory)
            run_continuous_episode(scenario, GreedyPublicPolicy(), AdaptivePartner(scenario),
                                   seed=1, output=output)
            self.assertTrue((output / "public_observations.jsonl").exists())
            self.assertTrue((output / "policy_io.jsonl").exists())
            self.assertTrue((output / "scenario.json").exists())


if __name__ == "__main__":
    unittest.main()
