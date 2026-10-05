"""持续运行时的机制测试。"""
import unittest
import json
from dataclasses import asdict, replace
from pathlib import Path
from tempfile import TemporaryDirectory

from hrc_pilot.continuous import (
    AdaptivePartner,
    CONTINUOUS_SCENARIOS,
    ContinuousWorld,
    DynamicsSpec,
    FixedReplayPartner,
    GreedyPublicPolicy,
    ReactivePartner,
    generate_benchmark_suite,
    load_scenario_catalog,
    run_catalog,
    run_counterfactual_benchmark,
    run_history_counterfactual,
    run_continuous_episode,
    make_partner,
    make_history_counterfactual_scenario,
    run_paired_benchmark,
)
from hrc_pilot.protocol import Action, Message
from hrc_pilot.benchmark import ModelPolicy, decode_action, public_observation_dict
from hrc_pilot.dataset import aggregate_results, evaluate_dataset, generate_dataset, iter_dataset


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

    def test_partner_modes_have_distinct_information_boundaries(self):
        scenario = CONTINUOUS_SCENARIOS["concurrent_overlay"]
        world = ContinuousWorld(scenario)
        world.reset(0)
        for message in scenario.initial_messages():
            world.say(message)
        world.start_action(Action("transfer", "blue", "keep_blue"))
        fixed = FixedReplayPartner(scenario)
        reactive = ReactivePartner(scenario)
        fixed.reset(0)
        reactive.reset(0)
        self.assertEqual(fixed.step(world.observe()).command.intent, "approach")
        self.assertEqual(reactive.step(world.observe()).command.intent, "yield")

    def test_suite_has_structure_split_without_manifest(self):
        scenarios = generate_benchmark_suite(count_per_condition=2, seed=11, include_reference=False)
        self.assertEqual([scenario.condition for scenario in scenarios],
                         ["isolated", "isolated", "matched_serial", "matched_serial",
                          "compositional", "compositional", "held_out", "held_out"])
        self.assertEqual(scenarios[-1].structure.split, "test")
        self.assertTrue(scenarios[-1].structure.dependencies)
        self.assertEqual(scenarios[0].objects, scenarios[2].objects)
        self.assertEqual(scenarios[1].regions, scenarios[7].regions)

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
            public = json.loads((output / "public_scenario.json").read_text())
            self.assertEqual(public["task_family"], scenario.task_family)
            self.assertNotIn("human_targets", public)
            self.assertNotIn("robot_targets", public)
            self.assertNotIn("dynamics", public)
            metrics = (output / "metrics.json").read_text()
            self.assertIn("structure_family", metrics)
            self.assertIn("partner_mode", metrics)

    def test_robot_failure_is_public_and_causes_reassignment(self):
        from hrc_pilot.continuous import run_continuous_episode
        scenario = replace(CONTINUOUS_SCENARIOS["relay"], name="forced_failure",
                           dynamics=DynamicsSpec(robot_failure_probability=1.0,
                                                 robot_delay_probability=1.0,
                                                 max_delay_steps=2,
                                                 human_replan_sensitivity=1.0))
        result = run_continuous_episode(scenario, GreedyPublicPolicy(),
                                        AdaptivePartner(scenario), seed=5)
        self.assertGreaterEqual(result["robot_failures"], 1)
        self.assertGreaterEqual(result["robot_delay_steps"], 1)
        self.assertGreaterEqual(result["human_reassignments"], 1)
        self.assertIn("human:blue:tray_blue", result["completed_skills"])
        self.assertTrue(result["activity_success"])
        self.assertTrue(result["task_success"])
        self.assertFalse(result["robot_role_success"])

    def test_paired_runner_keeps_scenario_seed_and_mode_directories(self):
        scenario = replace(CONTINUOUS_SCENARIOS["relay"], name="paired_relay")
        with TemporaryDirectory() as directory:
            results = run_paired_benchmark(seed=7, output=Path(directory), scenarios=[scenario])
            self.assertEqual({result["partner_mode"] for result in results},
                             {"fixed_replay", "reactive", "adaptive"})
            self.assertTrue((Path(directory) / "adaptive" / "paired_relay" / "scenario.json").exists())
            self.assertEqual({result["seed"] for result in results}, {7})

    def test_activity_contract_contains_declarative_dependencies(self):
        activity = CONTINUOUS_SCENARIOS["relay"].resolved_activity()
        robot_item = next(item for item in activity.work_items if item.preferred_role == "robot")
        self.assertEqual(robot_item.prerequisites, ("human:red:tray_red",))
        self.assertEqual(activity.success_policy, "all_work_items")

    def test_dependency_blocks_submission_until_public_skill_is_complete(self):
        from hrc_pilot.continuous import ContinuousWorld
        scenario = CONTINUOUS_SCENARIOS["relay"]
        world = ContinuousWorld(scenario)
        world.reset(2)
        world.start_action(Action("transfer", "blue", "tray_blue"))
        for _ in range(80):
            world.tick()
            if world.robot_execution is None:
                break
        self.assertIn("robot_transfer_blocked", {event["kind"] for event in world.events})
        self.assertNotIn("robot:blue:tray_blue", world.completed_skills)

    def test_user_defined_scenario_round_trips_without_state_script(self):
        from hrc_pilot.continuous import scenario_from_dict, scenario_to_dict
        original = CONTINUOUS_SCENARIOS["relay"]
        restored = scenario_from_dict(scenario_to_dict(original))
        self.assertEqual(restored.name, original.name)
        self.assertEqual(restored.resolved_activity().work_items,
                         original.resolved_activity().work_items)
        self.assertEqual(restored.initial_messages(), original.initial_messages())

    def test_custom_task_family_round_trip_and_catalog_order(self):
        from hrc_pilot.continuous import scenario_to_dict
        first = replace(CONTINUOUS_SCENARIOS["relay"], name="z_task", task_family="handoff_sort")
        second = replace(CONTINUOUS_SCENARIOS["relay"], name="a_task", task_family="handoff_sort")
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "z.json").write_text(json.dumps(scenario_to_dict(first), ensure_ascii=False))
            (root / "a.json").write_text(json.dumps(scenario_to_dict(second), ensure_ascii=False))
            catalog = load_scenario_catalog(root)
        self.assertEqual([scenario.name for scenario in catalog], ["a_task", "z_task"])
        self.assertEqual([scenario.task_family for scenario in catalog], ["handoff_sort"] * 2)

    def test_activity_contract_round_trips_interaction_acts(self):
        from hrc_pilot.continuous import scenario_from_dict, scenario_to_dict
        original = CONTINUOUS_SCENARIOS["nested_support"]
        encoded = scenario_to_dict(original)
        self.assertTrue(encoded["activity"]["interaction_acts"])
        restored = scenario_from_dict(encoded)
        self.assertEqual(restored.resolved_activity().interaction_acts,
                         original.resolved_activity().interaction_acts)

    def test_adaptive_partner_updates_private_state_after_public_failure(self):
        from hrc_pilot.continuous import run_continuous_episode
        scenario = replace(CONTINUOUS_SCENARIOS["relay"], name="state_trace",
                           dynamics=DynamicsSpec(robot_failure_probability=1.0,
                                                 human_replan_sensitivity=1.0))
        with TemporaryDirectory() as directory:
            result = run_continuous_episode(scenario, GreedyPublicPolicy(),
                                            AdaptivePartner(scenario), seed=4,
                                            output=Path(directory))
            state_events = [json.loads(line) for line in
                            (Path(directory) / "events.jsonl").read_text().splitlines()
                            if line]
        self.assertGreater(result["human_state_updates"], 0)
        state_events = [event for event in state_events if event.get("kind") == "human_state_update"]
        self.assertTrue(any(event["reason"] == "robot_action_failed" for event in state_events))

    def test_counterfactual_runner_keeps_group_identity(self):
        scenario = replace(CONTINUOUS_SCENARIOS["relay"], name="counterfactual_relay")
        with TemporaryDirectory() as directory:
            results = run_counterfactual_benchmark(
                policy_specs=("greedy_public", "hrc_pilot.continuous:GreedyPublicPolicy"),
                seed=9, output=Path(directory), scenarios=[scenario], partner_mode="adaptive")
        self.assertEqual(len(results), 2)
        self.assertEqual({result["counterfactual_group"] for result in results},
                         {"counterfactual_relay:seed=9:partner=adaptive"})
        self.assertEqual({result["policy_name"] for result in results},
                         {"greedy_public", "hrc_pilot.continuous_GreedyPublicPolicy"})

    def test_dataset_generation_and_model_evaluation_preserve_episode_identity(self):
        with TemporaryDirectory() as directory:
            root = Path(directory) / "dataset"
            metadata = generate_dataset(output=root, count_per_condition=1, repeats=1, seed=13)
            episodes = iter_dataset(root)
            self.assertEqual(metadata["episode_count"], 4)
            self.assertEqual(len(episodes), 4)
            result_root = Path(directory) / "evaluation"
            summary = evaluate_dataset(dataset=root, output=result_root,
                                       policy_spec="greedy_public", split="test")
            self.assertEqual(summary["episode_count"], 1)
            self.assertTrue((result_root / "greedy_public" / "test").exists())
            self.assertIn("conflict_rate", summary["overall"])

    def test_dataset_generation_accepts_custom_scenario_directory(self):
        from hrc_pilot.continuous import scenario_to_dict
        with TemporaryDirectory() as directory:
            root = Path(directory)
            scenario_dir = root / "scenarios"
            scenario_dir.mkdir()
            scenario = replace(CONTINUOUS_SCENARIOS["relay"], name="custom_task",
                               task_family="tool_handoff")
            (scenario_dir / "custom.json").write_text(
                json.dumps(scenario_to_dict(scenario), ensure_ascii=False))
            metadata = generate_dataset(output=root / "dataset", scenario_dir=scenario_dir,
                                        suite=False, repeats=1, seed=3)
            episodes = iter_dataset(root / "dataset")
        self.assertEqual(metadata["episode_count"], 1)
        self.assertEqual(episodes[0][1].task_family, "tool_handoff")

    def test_history_counterfactual_changes_adaptive_follow_up(self):
        scenario = make_history_counterfactual_scenario()
        results = run_history_counterfactual(
            policy_specs=("greedy_public", "request_help_public"),
            seed=3, scenarios=[scenario])
        self.assertEqual(len(results), 2)
        self.assertTrue(all(result["task_success"] for result in results))
        failed = next(result for result in results if result["policy_name"] == "greedy_public")
        helped = next(result for result in results if result["policy_name"] == "request_help_public")
        self.assertGreaterEqual(failed["robot_failures"], 1)
        self.assertGreaterEqual(failed["human_reassignments"], 1)
        self.assertEqual(helped["robot_failures"], 0)
        self.assertGreater(failed["same_geometry_steps"], 0)
        self.assertGreater(helped["history_conditioned_action_divergence"], 0.0)
        self.assertIsNotNone(helped["history_conditioned_first_divergence_step"])

    def test_genesis_activity_evaluator_uses_work_items(self):
        from hrc_pilot.continuous_genesis import GenesisContinuousAdapter
        scenario = CONTINUOUS_SCENARIOS["relay"]

        class FakeWorkspace:
            def __init__(self):
                self.scenario = scenario
                self.regions = dict(scenario.regions)
                self._positions = {spec.name: list(spec.position) for spec in scenario.objects}

            def positions(self):
                return self._positions

            def held_by_human(self):
                return ()

        workspace = FakeWorkspace()
        adapter = GenesisContinuousAdapter(workspace, scenario=scenario)
        self.assertFalse(adapter.finished_activity())
        for item in scenario.resolved_activity().work_items:
            workspace._positions[item.object_id] = list(workspace.regions[item.destination])
        self.assertTrue(adapter.finished_activity())
        workspace.attachment = (scenario.resolved_activity().work_items[0].object_id, (0, 0, 0))
        self.assertFalse(adapter.finished_activity())

    def test_aggregate_exposes_adaptation_metrics(self):
        summary = aggregate_results([{
            "task_success": True, "activity_success": True, "robot_success": True,
            "human_success": True, "robot_role_success": True, "human_role_success": True,
            "completion_time_s": 1.0, "coordination_cost": 2.0, "conflict_rate": 0.1,
            "human_reassignments": 1, "public_replans": 1, "recovery_time_steps": 3,
            "human_trust_delta": -0.1, "human_reliability_delta": -0.2,
            "human_workload_delta": 0.1, "human_dependency_delta": 0.2,
            "response_latency_steps": 1.0, "human_corrections": 0,
            "blocked_transfers": 0, "contribution_complementarity": 1.0,
            "recovery_success": 1.0, "coordination_efficiency": 0.8,
            "recovery_status": "recovered_after_failure",
            "cobalance_score": 0.9,
            "structure_split": "test", "condition": "held_out", "structure_family": "x",
            "partner_mode": "adaptive", "policy_name": "p",
        }])
        self.assertEqual(summary["overall"]["episodes"], 1)
        self.assertEqual(summary["overall"]["recovery_time_steps"], 3.0)
        self.assertEqual(summary["overall"]["cobalance_score"], 0.9)
        self.assertEqual(summary["overall"]["recovery_status_counts"], {
            "no_failure": 0, "recovered_after_failure": 1, "failed_to_recover": 0})
        self.assertEqual(summary["overall"]["confidence_intervals_95"]["cobalance_score"], [0.9, 0.9])

    def test_recovery_status_distinguishes_no_failure_from_recovery(self):
        scenario = CONTINUOUS_SCENARIOS["relay"]
        result = run_continuous_episode(
            scenario, GreedyPublicPolicy(), make_partner(scenario, "adaptive"), seed=0)
        self.assertEqual(result["recovery_status"], "no_failure")
        self.assertIsNone(result["recovery_success"])

        failure_scenario = CONTINUOUS_SCENARIOS["robot_induced_rebalance"]
        recovered = run_continuous_episode(
            failure_scenario, GreedyPublicPolicy(), make_partner(failure_scenario, "adaptive"), seed=0)
        self.assertEqual(recovered["recovery_status"], "recovered_after_failure")
        self.assertEqual(recovered["recovery_success"], 1.0)
        self.assertGreaterEqual(recovered["robot_failures"], 1)

        persistent_failure = replace(
            scenario, max_steps=30,
            dynamics=replace(scenario.dynamics, robot_failure_probability=1.0,
                             handoff_on_failure_probability=0.0))
        failed = run_continuous_episode(
            persistent_failure, GreedyPublicPolicy(), make_partner(persistent_failure, "adaptive"), seed=0)
        self.assertFalse(failed["task_success"])
        self.assertEqual(failed["recovery_status"], "failed_to_recover")
        self.assertEqual(failed["recovery_success"], 0.0)
        self.assertEqual(failed["human_reassignments"], 0)
        self.assertGreaterEqual(failed["robot_failures"], 1)

    def test_reference_scenes_exercise_dynamic_events(self):
        results = {
            name: run_continuous_episode(
                scenario, GreedyPublicPolicy(), make_partner(scenario, "adaptive"), seed=0)
            for name, scenario in CONTINUOUS_SCENARIOS.items()
        }
        self.assertGreaterEqual(results["history_reinterpretation"]["robot_failures"], 1)
        self.assertGreaterEqual(results["robot_induced_rebalance"]["human_reassignments"], 1)
        self.assertGreaterEqual(results["leave_and_return"]["human_state_updates"], 1)


if __name__ == "__main__":
    unittest.main()
