import csv
import json
from pathlib import Path

from modal_app.train_anatomy import (
    FDI16_MD5,
    FDI16_URL,
    BASE_SHAPE_FLOW_FILE,
    TRAINING_CODE_COMMIT,
    assert_paired_sparse_condition_identity,
    build_finetune_config,
    finite_losses_from_log,
    finite_losses_from_training_log,
    evaluate_e3_engineering_gates,
    materialize_trainer_checkpoint,
    prepare_training_metadata_view,
    smoke_training_command,
    smoke_trainer_source_without_snapshots,
    training_entry_source_with_experiment_seed,
    sparse_flow_trainer_source_with_derived_rope_buffer,
    trust_region_trainer_source,
    teacher_consistency_flow_source,
    calibrated_teacher_consistency_flow_source,
    axial_band_balanced_teacher_shape_flow_source,
    e10_teacher_init_flow_source,
    e10_axial_sparse_flow_source,
    e11_bandwise_teacher_sparse_flow_source,
    e12_decoder_only_shape_vae_source,
    e12_basic_trainer_gradient_gate_source,
    e12_component_gradient_diagnostic_source,
    e12_controlled_scale_zero_step_source,
    e12_initial_log_scale_source,
    e15_regional_decoder_zero_step_source,
    compare_e12_encoder_states,
    summarize_e12_decoder_update_groups,
    build_e12_late_delta_hybrid_state,
    e10_post_update_probe_trainer_source,
    decoded_occupancy_flow_source,
    e9_gradient_diagnostic_flow_source,
    e9_family_diagnostic_command,
    e10_one_tooth_training_command,
    e12_one_tooth_training_command,
    e12_gradient_diagnostic_command,
    e12_controlled_scale_command,
    e15_regional_decoder_command,
    build_e12_shape_vae_config,
    e10_four_family_training_command,
    sparse_anchor_training_command,
    sparse_occupancy_metrics,
    compare_sparse_occupancies,
    characterize_sparse_support_error,
    build_crown_transition_weights_from_occupancy,
    compose_crown_residual_logits,
    align_sparse_support_integer_translation,
    qualify_r04_sparse_adapter_objective,
    r04b_lora_wrapper_source,
    r04b_install_adapter_flow_source,
    r04b_zero_step_sparse_loss_source,
    r04b_basic_zero_step_probe_source,
    r04c_install_trainable_adapter_flow_source,
    r04c_basic_one_step_probe_source,
    r05a_install_adapter_flow_source,
    r05a_regional_objective_sparse_loss_source,
    r05a_basic_zero_step_probe_source,
    r05b_install_trainable_adapter_flow_source,
    r05b_basic_one_step_probe_source,
    r04b_sparse_adapter_target,
    interpolate_sparse_task_vector,
    summarize_candidate_comparison,
    summarize_stage1_validation,
    summarize_e10_g2_screen,
    summarize_e12_g2_decoder_screen,
    summarize_r04d_four_family_screen,
    summarize_r0_stage_attribution,
    summarize_r01_conditioning_decomposition,
    summarize_r02_sparse_support_characterization,
    summarize_r03_alignment_decomposition,
    summarize_r04_sparse_adapter_objective,
    resolve_e12_g2_validation_cases,
    select_mixed_representation_ceiling_cases,
    training_command,
)


def test_e14_crown_residual_composition_is_bitwise_root_preserving():
    import inspect

    mask_source = inspect.getsource(build_crown_transition_weights_from_occupancy)
    compose_source = inspect.getsource(compose_crown_residual_logits)
    assert "max(range(3)" in mask_source
    assert "crown_is_upper = upper_count >= lower_count" in mask_source
    assert "progress.square() * (3.0 - 2.0 * progress)" in mask_source
    assert "torch.where(blend > 0, base + residual * blend, base)" in compose_source
    assert "base + residual * blend" not in compose_source.split("torch.where", 1)[0]


def test_e14_g1_is_exactly_one_step_and_fail_closed():
    source = (Path(__file__).parents[1] / "modal_app" / "train_anatomy.py").read_text(encoding="utf-8")
    source = source.split("def run_e14_g1_crown_refiner_one_step", 1)[1]
    source = source.split("\n@app.function", 1)[0]
    assert 'run_name: str = "stage1-e14-g1-crown-refiner-one-step-v3"' in source
    assert source.count("optimizer.step()") == 1
    assert '"optimizerSteps": 1' in source
    assert "strict=True" in source
    assert "rootLogitsByteIdentical" in source
    assert "rawDecodeExactRepeat" in source
    assert '"g2Authorized": passed' in source


def test_e14_g2_cache_preserves_the_final_test_split():
    source = (Path(__file__).parents[1] / "modal_app" / "train_anatomy.py").read_text(encoding="utf-8")
    source = source.split("def materialize_e14_g2_frozen_base_support", 1)[1]
    source = source.split("\n@app.function", 1)[0]
    assert 'Counter({"train": 64, "validation": 12})' in source
    assert '"untouchedTestCaseCount": 24' in source
    assert 'asset["split"] == "validation"' in source
    assert 'asset["split"] == "test"' not in source
    assert '"optimizerSteps": 0' in source


def test_e14_g2_short_response_is_bounded_and_family_gated():
    source = (Path(__file__).parents[1] / "modal_app" / "train_anatomy.py").read_text(encoding="utf-8")
    source = source.split("def run_e14_g2_short_response", 1)[1]
    source = source.split("\n@app.function", 1)[0]
    assert 'run_name: str = "stage1-e14-g2-short-response-v2"' in source
    assert "for step in range(1, 101)" in source
    assert "if step % 25 == 0" in source
    assert '"untouchedTestCaseCount": 24' in source
    assert 'family["premolar"] > 0.0 and family["molar"] > 0.0' in source
    assert "all(value >= -0.005 for value in family.values())" in source
    assert 'final["allRootLogitsByteIdentical"]' in source
    assert 'final["allRawDecodesExactRepeat"]' in source
    assert 'final["allTopologyPassed"]' in source
    assert '"g3Authorized": passed' in source


def test_e14_g2_alignment_mask_audit_is_zero_training_and_bounded():
    source = (Path(__file__).parents[1] / "modal_app" / "train_anatomy.py").read_text(encoding="utf-8")
    source = source.split("def audit_e14_g2_alignment_and_crown_masks", 1)[1]
    source = source.split("\n@app.function", 1)[0]
    assert 'audit_name: str = "stage1-e14-g2-alignment-mask-audit-v2"' in source
    assert '"optimizerSteps": 0' in source
    assert 'maximum_shift=6' in source
    assert 'Counter({"train": 64, "validation": 12})' in source
    assert 'median_global_closure >= 0.25' in source
    assert '"nextTrainingDesignAuthorized": passed' in source
    assert '"productionMutationPermitted": False' in source


def test_e14_g2b_family_trust_region_gate_is_isolated_and_bounded():
    source = (Path(__file__).parents[1] / "modal_app" / "train_anatomy.py").read_text(encoding="utf-8")
    source = source.split("def run_e14_g2b_family_trust_region_gate", 1)[1]
    source = source.split("\n@app.function", 1)[0]
    assert 'run_name: str = "stage1-e14-g2b-family-trust-region-v1"' in source
    assert 'optimizerStepsPerFamily": 1' in source
    assert 'lr=0.0001' in source
    assert '8.0 * preservation' in source
    assert 'expected_prefix = f"heads.{family_index}."' in source
    assert '"g2cResponseAuthorized": passed' in source
    assert '"g3Authorized": False' in source


def test_e14_g2c_response_is_balanced_bounded_and_fail_closed():
    source = (Path(__file__).parents[1] / "modal_app" / "train_anatomy.py").read_text(encoding="utf-8")
    source = source.split("def run_e14_g2c_family_response_screen", 1)[1]
    source = source.split("\n@app.function", 1)[0]
    assert 'run_name: str = "stage1-e14-g2c-family-response-v1"' in source
    assert "for step in range(1, 41)" in source
    assert "index = (step - 1) % 4" in source
    assert '"stepsPerFamily": 10' in source
    assert 'fm["premolar"] > 0 and fm["molar"] > 0' in source
    assert '"g3Authorized": passed' in source


def test_e14_g2d_margin_diagnostic_has_no_optimizer_and_fail_closed_scale_gate():
    source=(Path(__file__).parents[1]/"modal_app"/"train_anatomy.py").read_text(encoding="utf-8")
    source=source.split("def diagnose_e14_g2d_response_margin",1)[1].split("\n@app.function",1)[0]
    assert 'run_name: str = "stage1-e14-g2d-response-margin-v1"' in source
    assert 'scales=(1.0,2.0,4.0,8.0,16.0)' in source
    assert '"optimizerSteps":0' in source
    assert '"scaledCanaryAuthorized":selected is not None' in source
    assert '"g3Authorized":False' in source


def test_e14_g2e_signed_margin_canary_is_balanced_and_fail_closed():
    whole_source=(Path(__file__).parents[1]/"modal_app"/"train_anatomy.py").read_text(encoding="utf-8")
    decorator=whole_source.split("def run_e14_g2e_signed_margin_canary",1)[0].rsplit("@app.function",1)[1]
    source=whole_source.split("def run_e14_g2e_signed_margin_canary",1)[1].split("\n@app.function",1)[0]
    assert 'run_name: str = "stage1-e14-g2e-signed-margin-canary-v2"' in source
    assert 'gpu="L4"' in decorator
    assert '"candidateOccupiedVoxelCount":int(np.count_nonzero(candidate_binary))' in source
    assert "for step in range(1,21)" in source
    assert 'lr=0.005' in source
    assert 'F.relu(0.10-target_sign[disagreement]*candidate[disagreement])' in source
    assert '"stepsPerFamily":5' in source
    assert '"g2fAuthorized":passed' in source
    assert '"g3Authorized":False' in source


def test_e14_g2f_gain_diagnostic_is_zero_update_and_fail_closed():
    source=(Path(__file__).parents[1]/"modal_app"/"train_anatomy.py").read_text(encoding="utf-8")
    source=source.split("def diagnose_e14_g2f_signed_margin_gain",1)[1].split("\n@app.function",1)[0]
    assert 'run_name: str = "stage1-e14-g2f-signed-margin-gain-v1"' in source
    assert '"optimizerSteps":0' in source
    assert '(1.0,2.0,4.0,6.0,8.0,12.0,16.0)' in source
    assert 'row["totalOccupancyCrossings"]>0' in source
    assert 'row["familyMedianCrownChamferRelativeImprovement"]["premolar"]>0' in source
    assert 'row["familyMedianCrownChamferRelativeImprovement"]["molar"]>0' in source
    assert '"boundedTrainingAuthorized":selected is not None' in source
    assert '"g3Authorized":False' in source
    assert '"productionMutationPermitted":False' in source


def test_e14_g2g_balances_addition_and_removal_and_preserves_roots():
    source=(Path(__file__).parents[1]/"modal_app"/"train_anatomy.py").read_text(encoding="utf-8")
    source=source.split("def run_e14_g2g_class_balanced_family_response",1)[1].split("\n@app.function",1)[0]
    assert 'run_name: str = "stage1-e14-g2g-class-balanced-family-response-v1"' in source
    assert 'for step in range(1,401)' in source
    assert '0.5*missing_loss+0.5*extra_loss' in source
    assert 'compose_crown_residual_logits' in source
    assert 'row["allRootLogitsByteIdentical"]' in source
    assert 'fm["premolar"]>0 and fm["molar"]>0' in source
    assert '"expertReviewPackAuthorized":passed' in source
    assert '"g3Authorized":False' in source
    assert '"productionMutationPermitted":False' in source


def test_e14_g2h_adds_image_conditioning_without_relaxing_root_gate():
    source=(Path(__file__).parents[1]/"modal_app"/"train_anatomy.py").read_text(encoding="utf-8")
    source=source.split("def run_e14_g2h_image_conditioned_crown_adapter",1)[1].split("\n@app.function",1)[0]
    assert 'run_name: str = "stage1-e14-g2h-image-conditioned-crown-adapter-v1"' in source
    assert 'hashlib.sha256(payload).hexdigest()!=row["inputImageSha256"]' in source
    assert 'yz=features.unsqueeze(2)' in source
    assert 'xz=features.unsqueeze(3)' in source
    assert 'xy=features.unsqueeze(4)' in source
    assert 'for step in range(1,801)' in source
    assert '0.5*missing_loss+0.5*extra_loss' in source
    assert 'row["allRootLogitsByteIdentical"]' in source
    assert 'fm["premolar"]>0 and fm["molar"]>0' in source
    assert '"expertReviewPackAuthorized":passed' in source
    assert '"productionMutationPermitted":False' in source


def test_e14_g2i_limits_supervision_to_surface_band_and_projects_fragments():
    source=(Path(__file__).parents[1]/"modal_app"/"train_anatomy.py").read_text(encoding="utf-8")
    source=source.split("def run_e14_g2i_surface_band_crown_adapter",1)[1].split("\n@app.function",1)[0]
    assert 'run_name: str = "stage1-e14-g2i-surface-band-crown-adapter-v1"' in source
    assert 'ndimage.distance_transform_edt(~surface)<=2.0' in source
    assert 'supervised=(weights>0)&case["surfaceBand"]' in source
    assert 'preserve=(weights>0)&(~case["surfaceBand"])' in source
    assert 'root_anchor=((weights[0,0]==0)&base[0,0])' in source
    assert 'output[0,0][remove]=-0.25' in source
    assert 'for step in range(1,601)' in source
    assert 'fm["premolar"]>0 and fm["molar"]>0' in source
    assert '"expertReviewPackAuthorized":selected is not None' in source
    assert '"productionMutationPermitted":False' in source


def test_e14_g2j_qualifies_molar_signal_through_real_decoder_fail_closed():
    source=(Path(__file__).parents[1]/"modal_app"/"train_anatomy.py").read_text(encoding="utf-8")
    source=source.split("def qualify_e14_g2j_molar_adapter_through_decoder",1)[1].split("\n@app.function",1)[0]
    assert 'run_name: str = "stage1-e14-g2j-molar-decoder-qualification-v3"' in source
    assert 'run_root/"run-receipt.json"' in source
    assert '"status":"started"' in source
    assert 'len(molar_rows)!=3' in source
    assert 'sample_shape_slat_cascade' in source
    assert 'decode_shape_slat' in source
    assert 'slat.replace(slat.feats,slat.coords.contiguous())' in source
    assert 'coords.contiguous()' in source
    assert 'decoder.upsample=original_upsample' in source
    assert '"allSparseCoordinateGuardsExercised"' in source
    assert 'compare_meshes(reference,base_mesh' in source
    assert 'evaluate_regional_non_regression' in source
    assert 'float(np.median(improvements))>=0.05' in source
    assert '"expertReviewPackAuthorized":passed' in source
    assert '"optimizerSteps":0' in source
    assert '"productionMutationPermitted":False' in source


def test_e14_g2j_entrypoint_submits_server_side_without_waiting():
    source=(Path(__file__).parents[1]/"modal_app"/"train_anatomy.py").read_text(encoding="utf-8")
    source=source.split("def run_e14_g2j_molar_decoder_qualification",1)[1].split("\n@app.local_entrypoint",1)[0]
    assert "qualify_e14_g2j_molar_adapter_through_decoder.spawn()" in source
    assert ".remote()" not in source
    assert '"functionCallId": call.object_id' in source


def test_e14_g2k_composes_candidate_crown_without_training_or_production_mutation():
    source=(Path(__file__).parents[1]/"modal_app"/"train_anatomy.py").read_text(encoding="utf-8")
    source=source.split("def qualify_e14_g2k_topology_preserving_crown_composition",1)[1].split("\n@app.function",1)[0]
    assert 'run_name: str = "stage1-e14-g2k-topology-preserving-crown-composition-v1"' in source
    assert '"protectedHeight":0.72' in source
    assert '"fullTransferHeight":0.82' in source
    assert '"maximumDisplacementFraction":0.05' in source
    assert 'compose_candidate_crown_onto_baseline' in source
    assert 'np.array_equal(np.asarray(reloaded.faces),np.asarray(baseline.faces))' in source
    assert '"optimizerSteps":0' in source
    assert '"clinicalClaimPermitted":False' in source
    assert '"productionMutationPermitted":False' in source


def test_e14_g2l_root_registers_before_fixed_crown_transfer():
    source=(Path(__file__).parents[1]/"modal_app"/"train_anatomy.py").read_text(encoding="utf-8")
    source=source.split("def qualify_e14_g2l_root_registered_crown_composition",1)[1].split("\n@app.function",1)[0]
    assert 'run_name: str = "stage1-e14-g2l-root-registered-crown-composition-v1"' in source
    assert 'align_candidate_to_baseline_root' in source
    assert 'aligned,registration=align_candidate_to_baseline_root' in source
    assert 'compose_candidate_crown_onto_baseline(baseline,aligned' in source
    assert '"scaleApplied":False' in source
    assert '"optimizerSteps":0' in source
    assert '"clinicalClaimPermitted":False' in source
    assert '"productionMutationPermitted":False' in source


def test_e14_g2m_grafts_actual_candidate_crown_and_gates_the_seam():
    source=(Path(__file__).parents[1]/"modal_app"/"train_anatomy.py").read_text(encoding="utf-8")
    source=source.split("def qualify_e14_g2m_cut_stitch_crown_graft",1)[1].split("\n@app.function",1)[0]
    assert 'run_name: str = "stage1-e14-g2m-cut-stitch-crown-graft-v2"' in source
    assert '"cutSurfaceConsolidation"' in source
    assert 'align_candidate_to_baseline_root' in source
    assert 'graft_candidate_crown(baseline,aligned,cut_height=0.72)' in source
    assert 'graft_receipt["boundaryEdgeCount"]==0' in source
    assert 'graft_receipt["nonManifoldEdgeCount"]==0' in source
    assert 'graft_receipt["watertight"]' in source
    assert '"optimizerSteps":0' in source
    assert '"clinicalClaimPermitted":False' in source
    assert '"productionMutationPermitted":False' in source


def test_e14_image_verifies_numerical_runtime_before_gpu_start():
    source=(Path(__file__).parents[1]/"modal_app"/"train_anatomy.py").read_text(encoding="utf-8")
    image_source=source.split("e14_training_image = (",1)[1].split("\n)\n",1)[0]
    assert "assert np.ndarray" in image_source


def test_trellis_image_preserves_modal_source_import_root():
    source=(Path(__file__).parents[1]/"modal_app"/"images"/"trellis_gpu.py").read_text(encoding="utf-8")
    assert '"PYTHONPATH": f"{TRELLIS2_PATH}:/root"' in source


def test_stage1_pairing_requires_the_same_frozen_sparse_tensor_everywhere():
    digest = "a" * 64
    base = [{
        "id": "molar-1",
        "frozenSparseCondition": {"coordsSha256": digest},
        "boundary": {"sparseCoordsSha256": digest},
    }]
    candidate = [{
        "id": "molar-1",
        "frozenSparseCondition": {"coordsSha256": digest},
        "boundary": {"sparseCoordsSha256": digest},
    }]
    assert_paired_sparse_condition_identity(base, candidate)

    candidate[0]["boundary"]["sparseCoordsSha256"] = "b" * 64
    try:
        assert_paired_sparse_condition_identity(base, candidate)
    except RuntimeError as error:
        assert "Frozen sparse condition identity failed" in str(error)
    else:
        raise AssertionError("Expected sparse-condition drift to fail closed")


def _e10_g2_receipts(candidate_regression: bool = False):
    digest = "a" * 64
    regions = {
        name: {
            "available": True,
            "symmetricChamferPercentDiagonal": 0.2,
            "hausdorff95PercentDiagonal": 0.3,
            "surfaceFscoreAt2Percent": 0.9,
            "sampleShareAbsoluteError": 0.01,
        }
        for name in ("apicalRootProxy", "middleRootProxy", "cervicalProxy", "crownProxy")
    }
    topology = {"coincidentVertexWeldedTopology": {
        "componentCount": 1, "largestComponentAreaFraction": 1.0,
        "boundaryEdgeCount": 0, "nonManifoldEdgeCount": 0,
    }}
    base, candidate = [], []
    for family in ("incisor", "canine", "premolar", "molar"):
        common = {
            "id": family, "toothFamily": family,
            "frozenSparseCondition": {"coordsSha256": digest},
            "boundary": {"sparseCoordsSha256": digest},
            "repeatability": {"rawShapeExact": True}, "topology": topology,
        }
        axial = {"regions": regions, "robustPoleProxyErrorsPercentDiagonal": {
            "apical": 0.1, "coronal": 0.1,
        }}
        base.append({**common, "metrics": {
            "symmetricChamferPercentDiagonal": 1.0,
            "hausdorff95PercentDiagonal": 1.0,
            "surfaceFscoreAt2Percent": 0.8,
            "sortedExtentRelativeError": 0.1,
            "canonicalAxialAnatomyProxy": axial,
        }})
        candidate.append({**common, "metrics": {
            "symmetricChamferPercentDiagonal": 0.95,
            "hausdorff95PercentDiagonal": 1.0,
            "surfaceFscoreAt2Percent": 0.8,
            "sortedExtentRelativeError": 0.1,
            "canonicalAxialAnatomyProxy": axial,
        }})
    if candidate_regression:
        candidate[0]["topology"] = {"coincidentVertexWeldedTopology": {
            **topology["coincidentVertexWeldedTopology"], "boundaryEdgeCount": 2,
        }}
    return base, candidate


def test_e10_g2_screen_requires_all_four_families_to_pass():
    base, candidate = _e10_g2_receipts()
    result = summarize_e10_g2_screen(base, candidate)
    assert result["passed"] is True
    assert result["g3Authorized"] is True
    assert set(result["familyChamfer"]) == {"incisor", "canine", "premolar", "molar"}

    base, candidate = _e10_g2_receipts(candidate_regression=True)
    result = summarize_e10_g2_screen(base, candidate)
    assert result["passed"] is False
    assert result["g3Authorized"] is False


def test_e10_g2_command_is_sealed_to_four_family_view():
    command = e10_four_family_training_command(
        "toothfairy-stage1-v1", "stage1-e10-g2-four-family-v1"
    )
    data_spec = json.loads(command[command.index("--data_dir") + 1])
    paths = next(iter(data_spec.values()))
    assert all("e10_g2_four_family_v1" in path for path in paths.values())
    assert command[-2:] == ["--auto_retry", "0"]


def test_e11_teacher_preservation_is_equal_per_axial_band_and_fail_closed():
    source = (
        "class SparseFlowMatchingTrainer:\n"
        "    def training_losses(self, x_0, cond=None, **kwargs):\n"
        "        pred = self.training_models['denoiser'](x_t, t * 1000, cond, **kwargs)\n"
        "        assert pred.shape == noise.shape == x_0.shape\n"
        "        target = self.get_v(x_0, noise, t)\n"
        "        terms[\"mse\"] = F.mse_loss(pred.feats, target.feats)\n"
        "        terms[\"loss\"] = terms[\"mse\"]\n"
    )
    patched = e11_bandwise_teacher_sparse_flow_source(source)
    assert "teacher_sample_losses" in patched
    assert "band_teacher_losses" in patched
    assert "equal-per-sample-per-axial-band" in patched
    assert "teacherBandMseMin" in patched
    assert "teacherBandMseMax" in patched
    assert "F.mse_loss(pred.feats.float(), teacher_pred.feats.float())" not in patched
    try:
        e11_bandwise_teacher_sparse_flow_source("class SparseFlowMatchingTrainer: pass\n")
    except ValueError as error:
        assert "refusing E10 patch" in str(error)
    else:
        raise AssertionError("Expected changed upstream sparse loss to fail closed")


def test_e12_shape_vae_patch_freezes_encoder_and_seals_native_geometry_terms():
    source = (
        "class ShapeVaeTrainer:\n"
        "    def __init__(self, *args, lambda_subdiv=0.1, **kwargs):\n"
        "    ):\n"
        "        super().__init__(*args, **kwargs)\n"
        "        self.lambda_subdiv = lambda_subdiv\n"
        "    def training_losses(self):\n"
        "        z, mean, logvar = self.training_models['encoder'](vertices, intersected, sample_posterior=True, return_raw=True)\n"
        "        recon, pred_vertice, pred_intersected, subs_gt, subs = self.training_models['decoder'](z, intersected)\n"
        "        # subdivision prediction loss\n"
        "        for i, (sub_gt, sub) in enumerate(zip(subs_gt, subs)):\n"
        "            pass\n"
        "        terms[\"loss\"] = terms[\"loss\"] + self.lambda_kl * terms[\"kl\"]\n"
        "            \n"
        "        return terms, {}\n"
    )
    patched = e12_decoder_only_shape_vae_source(source)
    assert patched.index("models['encoder'].train().requires_grad_(False)") < patched.index(
        "super().__init__(*args, **kwargs)"
    )
    assert "optimizer contains encoder parameters" in patched
    assert "decoder-only-native-geometry-v1" in patched
    for term in (
        "direct/intersected", "direct/vertice", "render/mask", "render/depth",
        "render/normal/l1", "render/normal/ssim", "render/normal/lpips", "bce_sub",
    ):
        assert term in patched
    assert "DENTALSCULPTOR_E12_OBJECTIVE_RECEIPT" in patched
    assert "missing_subdivision_targets" in patched
    assert "subdivisionTargetLevels" in patched
    assert "z.feats.detach().requires_grad_(True)" in patched
    assert "latentLeafGradEnabled" in patched
    assert "SubMConv3d_neighbor_cache_" in patched
    assert "removedInferenceNeighborCaches" in patched
    try:
        e12_decoder_only_shape_vae_source("class ShapeVaeTrainer: pass\n")
    except ValueError as error:
        assert "refusing E12 patch" in str(error)
    else:
        raise AssertionError("Expected changed upstream ShapeVaeTrainer source to fail closed")


def test_e15_regional_decoder_gate_is_zero_step_late_only_and_fail_closed():
    source = (
        "class ShapeVaeTrainer:\n"
        "    def __init__(self, *args, lambda_subdiv=0.1, **kwargs):\n"
        "    ):\n"
        "        super().__init__(*args, **kwargs)\n"
        "        self.lambda_subdiv = lambda_subdiv\n"
        "    def training_losses(self):\n"
        "        z, mean, logvar = self.training_models['encoder'](vertices, intersected, sample_posterior=True, return_raw=True)\n"
        "        recon, pred_vertice, pred_intersected, subs_gt, subs = self.training_models['decoder'](z, intersected)\n"
        "\n"
        "        terms = edict(loss = 0.0)\n"
        "        # subdivision prediction loss\n"
        "        for i, (sub_gt, sub) in enumerate(zip(subs_gt, subs)):\n"
        "            pass\n"
        "        terms[\"loss\"] = terms[\"loss\"] + self.lambda_kl * terms[\"kl\"]\n"
        "            \n"
        "        return terms, {}\n"
    )
    patched = e15_regional_decoder_zero_step_source(source)
    assert "late_prefixes = ('blocks.3.', 'output_layer.')" in patched
    assert "dentalsculptor_e15_teacher" in patched
    assert "candidate/target sparse coordinates do not align" in patched
    assert "crown_intersected" in patched
    assert "cervical_intersected_teacher" in patched
    assert "root_intersected_teacher" in patched
    assert "engineeringMaskOnly" in patched
    assert "optimizerSteps': 0" in patched
    assert "DENTALSCULPTOR_E15_REGIONAL_DECODER_ZERO_STEP_COMPLETE" in patched
    assert "optimizer.step" not in patched
    try:
        e15_regional_decoder_zero_step_source("class ShapeVaeTrainer: pass\n")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected changed E15 trainer boundary to fail closed")


def test_e12_gradient_gate_is_before_optimizer_boundary_and_fail_closed():
    source = (
        "        ## gradient clip\n"
        "        if self.grad_clip is not None:\n"
        "            pass\n"
        "        ## step\n"
        "        self.optimizer.step()\n"
    )
    patched = e12_basic_trainer_gradient_gate_source(source)
    assert patched.index("missing_gradients") < patched.index("## gradient clip")
    assert patched.index("nonfinite_gradients") < patched.index("self.optimizer.step()")
    try:
        e12_basic_trainer_gradient_gate_source("def run_step(self): pass\n")
    except ValueError as error:
        assert "gradient boundary changed" in str(error)
    else:
        raise AssertionError("Expected changed upstream BasicTrainer source to fail closed")


def test_e12_component_gradient_diagnostic_is_zero_step_and_fail_closed():
    source = (
        "class ShapeVaeTrainer:\n"
        "    def training_losses(self):\n"
        "        terms = {}\n"
        "            \n"
        "        return terms, {}\n"
    )
    patched = e12_component_gradient_diagnostic_source(source)
    assert "zero-step-unscaled-component-autograd" in patched
    assert "torch.autograd.grad" in patched
    assert "optimizer.step" not in patched
    assert patched.index("component_receipts") < patched.index("return terms, {}")
    try:
        e12_component_gradient_diagnostic_source("class ShapeVaeTrainer: pass\n")
    except ValueError as error:
        assert "return boundary changed" in str(error)
    else:
        raise AssertionError("Expected changed E12 return boundary to fail closed")


def test_e12_controlled_scale_probe_stops_before_optimizer_and_is_fail_closed():
    source = (
        "class BasicTrainer:\n"
        "    def init_models_and_more(self):\n"
        "        if self.mix_precision_dtype == torch.float16:\n"
        "                self.log_scale = 20.0\n"
        "    def run_step(self):\n"
        "        ## gradient clip\n"
        "        if self.grad_clip is not None:\n"
        "            pass\n"
        "        ## step\n"
        "        self.optimizer.step()\n"
    )
    patched = e12_controlled_scale_zero_step_source(source, log_scale=12)
    assert "self.log_scale = 12.0" in patched
    assert "normal-inflat-all-backward-controlled-scale" in patched
    assert patched.index("CONTROLLED_SCALE_COMPLETE_ZERO_STEP") < patched.index("self.optimizer.step()")
    assert "allZeroGradientCount" in patched
    for bad_source in (
        source.replace("self.log_scale = 20.0", "self.log_scale = 19.0"),
        source.replace("## gradient clip", "## changed clip"),
    ):
        try:
            e12_controlled_scale_zero_step_source(bad_source, log_scale=12)
        except ValueError:
            pass
        else:
            raise AssertionError("Expected changed controlled-scale boundary to fail closed")


def test_e12_initial_scale_patch_is_sealed_and_fail_closed():
    source = "        if enabled:\n                self.log_scale = 20.0\n"
    patched = e12_initial_log_scale_source(source, log_scale=12)
    assert "self.log_scale = 12.0" in patched
    assert "dentalsculptor_e12_initial_log_scale = 12.0" in patched
    for bad_source, bad_scale in ((source.replace("20.0", "19.0"), 12), (source, 11)):
        try:
            e12_initial_log_scale_source(bad_source, log_scale=bad_scale)
        except ValueError:
            pass
        else:
            raise AssertionError("Expected changed E12 scale contract to fail closed")


def test_e12_encoder_identity_distinguishes_dtype_conversion_from_real_change():
    import numpy as np

    base = {
        "weight": np.array([1.0, 2.0], dtype=np.float32),
        "count": np.array([3], dtype=np.int64),
    }
    dtype_only = {
        "weight": np.array([1.0, 2.0], dtype=np.float16),
        "count": np.array([3], dtype=np.int64),
    }
    result = compare_e12_encoder_states(base, dtype_only)
    assert result["classification"] == "dtype-or-serialization-only"
    assert result["canonicalRuntimeEquivalent"] is True
    assert result["dtypeChangedTensorCount"] == 1
    changed = {**dtype_only, "weight": np.array([1.0, 2.5], dtype=np.float16)}
    result = compare_e12_encoder_states(base, changed)
    assert result["classification"] == "genuine-state-change"
    assert result["canonicalRuntimeEquivalent"] is False
    assert result["canonicalChangedTensorCount"] == 1


def test_e12_g2_requires_crown_gain_and_preserves_every_engineering_gate():
    regions = {
        name: {
            "available": True,
            "symmetricChamferPercentDiagonal": 1.0,
            "hausdorff95PercentDiagonal": 1.0,
            "surfaceFscoreAt2Percent": 0.8,
            "sampleShareAbsoluteError": 0.01,
        }
        for name in ("apicalRootProxy", "middleRootProxy", "cervicalProxy", "crownProxy")
    }
    topology = {"coincidentVertexWeldedTopology": {
        "componentCount": 1, "largestComponentAreaFraction": 1.0,
        "boundaryEdgeCount": 0, "nonManifoldEdgeCount": 0,
    }}
    base, candidate = [], []
    for index, family in enumerate(("incisor", "canine", "premolar", "molar")):
        case_id = f"case-{index}"
        common = {
            "id": case_id, "toothFamily": family,
            "frozenLatentSha256": f"latent-{index}",
            "boundary": {"inputLatentSha256": f"latent-{index}"},
            "repeatability": {"rawShapeExact": True}, "topology": topology,
        }
        base.append({**common, "metrics": {
            "symmetricChamferPercentDiagonal": 1.0,
            "canonicalAxialAnatomyProxy": {
                "regions": regions,
                "robustPoleProxyErrorsPercentDiagonal": {"apical": 0.2, "coronal": 0.2},
            },
        }})
        candidate_regions = {name: dict(values) for name, values in regions.items()}
        candidate_regions["crownProxy"]["symmetricChamferPercentDiagonal"] = (
            0.9 if index < 3 else 1.0
        )
        candidate.append({**common, "metrics": {
            "symmetricChamferPercentDiagonal": 0.98,
            "canonicalAxialAnatomyProxy": {
                "regions": candidate_regions,
                "robustPoleProxyErrorsPercentDiagonal": {"apical": 0.2, "coronal": 0.2},
            },
        }})
    result = summarize_e12_g2_decoder_screen(base, candidate)
    assert result["passed"] is True
    assert result["familiesWithCrownChamferImprovement"] == 3
    assert result["e13Authorized"] is True


def test_r04d_requires_matched_inputs_three_family_crown_gain_and_root_safety():
    regions = {
        name: {
            "available": True,
            "symmetricChamferPercentDiagonal": 1.0,
            "hausdorff95PercentDiagonal": 1.0,
            "surfaceFscoreAt2Percent": 0.8,
            "sampleShareAbsoluteError": 0.01,
        }
        for name in ("apicalRootProxy", "middleRootProxy", "cervicalProxy", "crownProxy")
    }
    topology = {"coincidentVertexWeldedTopology": {
        "componentCount": 1, "largestComponentAreaFraction": 1.0,
        "boundaryEdgeCount": 0, "nonManifoldEdgeCount": 0,
    }}
    base, candidate = [], []
    for index, family in enumerate(("incisor", "canine", "premolar", "molar")):
        common = {
            "id": f"case-{index}", "toothFamily": family,
            "inputImageSha256": f"image-{index}",
            "referenceMeshSha256": f"mesh-{index}",
            "generationSeed": index, "quality": "preview",
            "repeatability": {"rawShapeExact": True}, "topology": topology,
        }
        base.append({**common, "metrics": {
            "symmetricChamferPercentDiagonal": 1.0,
            "canonicalAxialAnatomyProxy": {
                "regions": regions,
                "robustPoleProxyErrorsPercentDiagonal": {"apical": 0.2, "coronal": 0.2},
            },
        }})
        candidate_regions = {name: dict(values) for name, values in regions.items()}
        candidate_regions["crownProxy"]["symmetricChamferPercentDiagonal"] = (
            0.9 if index < 3 else 1.0
        )
        candidate.append({**common, "metrics": {
            "symmetricChamferPercentDiagonal": 0.99,
            "canonicalAxialAnatomyProxy": {
                "regions": candidate_regions,
                "robustPoleProxyErrorsPercentDiagonal": {"apical": 0.2, "coronal": 0.2},
            },
        }})
    result = summarize_r04d_four_family_screen(base, candidate)
    assert result["passed"] is True
    assert result["familiesWithCrownChamferImprovement"] == 3
    assert result["boundedTrainingAuthorized"] is True
    assert result["productionPromotionPermitted"] is False

    candidate[0] = {**candidate[0], "generationSeed": 99}
    try:
        summarize_r04d_four_family_screen(base, candidate)
    except RuntimeError as error:
        assert "matched-input contract" in str(error)
    else:
        raise AssertionError("R0.4D must reject mismatched paired inputs")


def _r0_stage_attribution_receipts(product_multiplier: float = 2.0):
    oracle, product = [], []
    for family in ("incisor", "canine", "premolar", "molar"):
        for index in range(3):
            case_id = f"{family}-{index}"
            common = {
                "id": case_id,
                "toothFamily": family,
                "groupId": f"patient-{family}-{index}",
                "referenceMeshSha256": f"{len(oracle) + 1:064x}",
            }
            def metrics(multiplier: float):
                return {"canonicalAxialAnatomyProxy": {"regions": {
                    "crownProxy": {"symmetricChamferPercentDiagonal": 0.5 * multiplier},
                    "apicalRootProxy": {"symmetricChamferPercentDiagonal": 0.4 * multiplier},
                    "middleRootProxy": {"symmetricChamferPercentDiagonal": 0.6 * multiplier},
                }}}
            oracle.append({**common, "metrics": metrics(1.0)})
            product.append({**common, "metrics": metrics(product_multiplier)})
    return oracle, product


def test_r0_attributes_large_product_gap_to_image_conditioned_generation():
    oracle, product = _r0_stage_attribution_receipts()
    result = summarize_r0_stage_attribution(oracle, product)
    assert result["caseCount"] == 12
    assert result["familyCounts"] == {
        "incisor": 3, "canine": 3, "premolar": 3, "molar": 3,
    }
    assert result["medianProductToOracleCrownErrorRatio"] == 2.0
    assert result["oracleCrownCeilingAdequateForAttribution"] is True
    assert result["dominantMeasuredBoundary"] == "image-conditioned-generation"
    assert result["trainingBoundaryRecommendation"] == "image-conditioned-shape-inference"
    assert result["clinicalClaimPermitted"] is False
    assert result["productionPromotionPermitted"] is False


def test_r0_fails_closed_on_pairing_or_family_drift():
    oracle, product = _r0_stage_attribution_receipts()
    product[0]["referenceMeshSha256"] = "f" * 64
    try:
        summarize_r0_stage_attribution(oracle, product)
    except ValueError as error:
        assert "pairing drift" in str(error)
    else:
        raise AssertionError("Expected R0 reference drift to fail closed")

    oracle, product = _r0_stage_attribution_receipts()
    oracle[0]["toothFamily"] = "molar"
    try:
        summarize_r0_stage_attribution(oracle, product)
    except ValueError as error:
        assert "three cases per tooth family" in str(error)
    else:
        raise AssertionError("Expected R0 family imbalance to fail closed")


def test_r0_reports_root_missingness_without_discarding_a_valid_crown_case():
    oracle, product = _r0_stage_attribution_receipts()
    del product[0]["metrics"]["canonicalAxialAnatomyProxy"]["regions"][
        "apicalRootProxy"
    ]["symmetricChamferPercentDiagonal"]
    result = summarize_r0_stage_attribution(oracle, product)
    assert result["caseCount"] == 12
    assert result["casesWithBothRootProxyBands"] == 11
    first = next(row for row in result["cases"] if row["id"] == "incisor-0")
    assert first["comparedRootRegions"] == ["middleRootProxy"]


def test_r01_attributes_gap_closed_by_reference_support_to_sparse_structure():
    oracle, product = _r0_stage_attribution_receipts(product_multiplier=4.0)
    support = []
    for row in oracle:
        cloned = json.loads(json.dumps(row))
        regions = cloned["metrics"]["canonicalAxialAnatomyProxy"]["regions"]
        for values in regions.values():
            values["symmetricChamferPercentDiagonal"] *= 1.5
        support.append(cloned)
    result = summarize_r01_conditioning_decomposition(oracle, product, support)
    assert result["caseCount"] == 12
    assert result["medianCrownGapFractionClosedByReferenceSupport"] > 0.8
    assert result["dominantMeasuredSubBoundary"] == "image-to-sparse-structure"
    assert result["trainingAuthorized"] is False


def test_r01_attributes_small_gap_closure_to_shape_features():
    oracle, product = _r0_stage_attribution_receipts(product_multiplier=4.0)
    support = json.loads(json.dumps(product))
    result = summarize_r01_conditioning_decomposition(oracle, product, support)
    assert result["medianCrownGapFractionClosedByReferenceSupport"] == 0.0
    assert result["dominantMeasuredSubBoundary"] == "image-conditioned-shape-features"


def test_r02_characterizes_missing_crown_occupancy_and_summarizes_families():
    import numpy as np

    reference = np.asarray([
        [x, y, z] for z in range(8) for x in range(2) for y in range(2)
    ], dtype=np.int64)
    predicted = reference[reference[:, 2] < 7]
    metrics = characterize_sparse_support_error(reference, predicted, resolution=64)
    assert metrics["global"]["precision"] == 1.0
    assert metrics["global"]["recall"] < 1.0
    assert metrics["bands"]["crownProxy"]["missingVoxelCount"] > 0
    assert metrics["coronalPoleAbsoluteErrorVoxels"] == 1

    receipts, responses = [], []
    for family_index, family in enumerate(("incisor", "canine", "premolar", "molar")):
        for case_index in range(3):
            case_id = f"{family}-{case_index}"
            receipts.append({
                "id": case_id, "toothFamily": family, "metrics": metrics,
            })
            responses.append({
                "id": case_id,
                "crownGapFractionClosedByReferenceSupport": (
                    0.80 + family_index * 0.02 + case_index * 0.01
                ),
            })
    summary = summarize_r02_sparse_support_characterization(
        receipts, {"cases": responses}
    )
    assert summary["caseCount"] == 12
    assert summary["dominantSparseErrorPattern"] == "missing-reference-occupancy"
    assert summary["weakestMedianRecallBand"] == "crownProxy"
    assert summary["adapterDesignAuthorized"] is True
    assert summary["optimizerRunAuthorized"] is False


def test_r03_recovers_a_known_integer_translation_and_attributes_alignment():
    import numpy as np

    reference = np.asarray([
        [x, y, z] for z in range(8, 16) for x in range(8, 12) for y in range(9, 13)
    ], dtype=np.int64)
    predicted = reference + np.asarray([2, -1, 3], dtype=np.int64)
    alignment = align_sparse_support_integer_translation(reference, predicted)
    assert alignment["bestTranslationXYZ"] == [-2, 1, -3]
    assert alignment["aligned"]["global"]["voxelIoU"] == 1.0
    receipts = []
    for family in ("incisor", "canine", "premolar", "molar"):
        for index in range(3):
            receipts.append({
                "id": f"{family}-{index}",
                "toothFamily": family,
                "alignment": alignment,
            })
    summary = summarize_r03_alignment_decomposition(receipts)
    assert summary["dominantMeasuredSubBoundary"] == "coordinate-frame-alignment"
    assert summary["adapterObjectiveDesignAuthorized"] is False
    assert summary["optimizerRunAuthorized"] is False


def test_r04_zero_step_objective_has_complete_gradients_and_stays_read_only():
    import numpy as np
    import pytest

    pytest.importorskip("torch")

    reference = np.asarray([
        [x, y, z] for z in range(8, 17) for x in range(8, 12) for y in range(9, 13)
    ], dtype=np.int64)
    predicted_rows = set(map(tuple, reference.tolist()))
    predicted_rows.remove((8, 9, 16))
    predicted_rows.remove((9, 9, 16))
    predicted_rows.add((12, 12, 16))
    predicted_rows.add((12, 13, 16))
    predicted = np.asarray(sorted(predicted_rows), dtype=np.int64)
    probe = qualify_r04_sparse_adapter_objective(reference, predicted)
    assert probe["optimizerSteps"] == 0
    assert probe["missingCrownVoxelCount"] == 2
    assert probe["extraCrownVoxelCount"] == 2
    assert probe["finiteObjectiveTerms"] is True
    assert probe["everyAdapterTensorFiniteNonzeroGradient"] is True
    assert probe["nonCrownPreservationGradientActive"] is True
    assert probe["modelIntegrationAuthorized"] is True
    assert probe["oneStepIntegrationAuthorized"] is False

    receipts = []
    for family in ("incisor", "canine", "premolar", "molar"):
        for index in range(3):
            receipts.append({
                "id": f"{family}-{index}", "toothFamily": family, "probe": probe,
            })
    summary = summarize_r04_sparse_adapter_objective(receipts)
    assert summary["qualifiedCaseCount"] == 12
    assert summary["modelIntegrationAuthorized"] is True
    assert summary["optimizerRunAuthorized"] is False


def test_r04b_target_is_the_final_sparse_transformer_mlp_projection():
    config = {
        "models": {"denoiser": {
            "name": "SparseStructureFlowModel",
            "args": {"num_blocks": 24, "model_channels": 1536},
        }}
    }
    assert r04b_sparse_adapter_target(config) == "blocks.23.mlp.mlp.2"
    wrapper = r04b_lora_wrapper_source()
    assert wrapper.startswith("import torch\n")
    assert "rank != 4" in wrapper
    assert "self.base = base.requires_grad_(False)" in wrapper
    assert "lora_down" in wrapper and "lora_up" in wrapper


def test_r04b_source_patches_are_fail_closed_and_zero_step():
    parent = (
        "class FlowMatchingTrainer:\n"
        "    def __init__(self, *args, t_schedule=None, **kwargs):\n"
        "        super().__init__(*args, **kwargs)\n"
        "        self.t_schedule = t_schedule\n"
    )
    sparse = (
        "class SparseFlowMatchingTrainer:\n"
        "    def training_losses(self):\n"
        "        terms[\"mse\"] = F.mse_loss(pred.feats, target.feats)\n"
        "        terms[\"loss\"] = terms[\"mse\"]\n"
    )
    patched_parent = r04b_install_adapter_flow_source(parent)
    patched_sparse = r04b_zero_step_sparse_loss_source(sparse)
    assert "model.blocks[29].mlp.mlp[2]" in patched_parent
    assert "parameter.requires_grad_(False)" in patched_parent
    assert "frozenStateByteIdentical" in patched_sparse
    assert "torch.autograd.grad" in patched_sparse
    assert "optimizer.step" not in patched_sparse
    assert "DENTALSCULPTOR_R04B_ZERO_STEP_COMPLETE" in patched_sparse


def test_e12_g2_validation_join_is_unique_and_hash_bound():
    digest = "a" * 64
    validation = {"cases": [{
        "id": "case-1", "toothFamily": "incisor", "groupId": "patient-1",
        "fdiNumber": 11, "referenceMesh": "validation/tooth.ply",
        "referenceMeshSha256": digest,
    }]}
    manifest = {"assets": [{
        "id": "case-1", "toothFamily": "incisor", "groupId": "patient-1",
        "fdiNumber": 11, "split": "validation",
        "canonicalPath": "validation/tooth.ply", "canonicalSha256": digest,
    }]}
    resolved = resolve_e12_g2_validation_cases(validation, manifest, ("incisor",))
    assert resolved[0]["canonicalSha256"] == digest
    manifest["assets"][0]["canonicalSha256"] = "b" * 64
    try:
        resolve_e12_g2_validation_cases(validation, manifest, ("incisor",))
    except ValueError as error:
        assert "manifest join drift" in str(error)
    else:
        raise AssertionError("Expected mismatched reference hash to fail closed")


def test_e12_decoder_delta_localization_separates_late_and_early_stages():
    import numpy as np

    base = {
        "from_latent.weight": np.zeros((2,), dtype=np.float32),
        "blocks.0.conv.weight": np.zeros((2,), dtype=np.float32),
        "blocks.3.conv.weight": np.zeros((2,), dtype=np.float32),
        "output_layer.weight": np.zeros((2,), dtype=np.float32),
    }
    candidate = {key: value.astype(np.float16) for key, value in base.items()}
    candidate["blocks.0.conv.weight"][0] = np.float16(0.25)
    candidate["blocks.3.conv.weight"][0] = np.float16(0.5)
    candidate["output_layer.weight"][1] = np.float16(0.125)
    result = summarize_e12_decoder_update_groups(base, candidate)
    assert result["changedTensorCount"] == 3
    assert result["groups"]["blocks.0"]["changedTensorCount"] == 1
    assert result["groups"]["blocks.3"]["changedTensorCount"] == 1
    assert result["groups"]["output_layer"]["changedTensorCount"] == 1
    assert result["lateDeltaHybridAuthorized"] is True


def test_e12_late_delta_hybrid_preserves_early_decoder_exactly():
    import numpy as np

    base = {
        "from_latent.weight": np.asarray([1.0]),
        "blocks.0.conv.weight": np.asarray([2.0]),
        "blocks.3.conv.weight": np.asarray([3.0]),
        "output_layer.weight": np.asarray([4.0]),
    }
    candidate = {key: value + 10.0 for key, value in base.items()}
    hybrid, late_keys = build_e12_late_delta_hybrid_state(base, candidate)
    assert late_keys == ["blocks.3.conv.weight", "output_layer.weight"]
    assert hybrid["from_latent.weight"] is base["from_latent.weight"]
    assert hybrid["blocks.0.conv.weight"] is base["blocks.0.conv.weight"]
    assert hybrid["blocks.3.conv.weight"] is candidate["blocks.3.conv.weight"]
    assert hybrid["output_layer.weight"] is candidate["output_layer.weight"]

    output_only, output_keys = build_e12_late_delta_hybrid_state(
        base, candidate, ("output_layer.",)
    )
    assert output_keys == ["output_layer.weight"]
    assert output_only["blocks.3.conv.weight"] is base["blocks.3.conv.weight"]
    assert output_only["output_layer.weight"] is candidate["output_layer.weight"]

    block3_only, block3_keys = build_e12_late_delta_hybrid_state(
        base, candidate, ("blocks.3.",)
    )
    assert block3_keys == ["blocks.3.conv.weight"]
    assert block3_only["blocks.3.conv.weight"] is candidate["blocks.3.conv.weight"]
    assert block3_only["output_layer.weight"] is base["output_layer.weight"]


def test_e12_g1_config_and_command_are_decoder_only_and_sealed():
    base = {
        "models": {"encoder": {}, "decoder": {}},
        "dataset": {"name": "FlexiDualGridDataset", "args": {"resolution": 512}},
        "trainer": {
            "name": "ShapeVaeTrainer",
            "args": {
                "max_steps": 100,
                "batch_size_per_gpu": 4,
                "batch_split": 2,
                "optimizer": {"name": "AdamW", "args": {"lr": 1e-5}},
            },
        },
    }
    config = build_e12_shape_vae_config(base, "/encoder.pt", "/decoder.pt")
    args = config["trainer"]["args"]
    assert args["finetune_ckpt"] == {"encoder": "/encoder.pt", "decoder": "/decoder.pt"}
    assert args["max_steps"] == args["i_save"] == 1
    assert args["optimizer"]["args"]["lr"] == 1e-6
    assert args["dentalsculptor_e12_objective"] == "decoder-only-native-geometry-v1"
    command = e12_one_tooth_training_command(
        "toothfairy-stage1-v1", "stage1-e12-g1-one-tooth-v7"
    )
    data = json.loads(command[command.index("--data_dir") + 1])
    paths = next(iter(data.values()))
    assert set(paths) == {"base", "mesh_dump", "dual_grid"}
    assert all("e12_g1_one_tooth_v6" in path for path in paths.values())
    assert command[-2:] == ["--auto_retry", "0"]
    diagnostic = e12_gradient_diagnostic_command(
        "toothfairy-stage1-v1", "stage1-e12-g1-gradient-diagnostic-v1"
    )
    diagnostic_data = json.loads(diagnostic[diagnostic.index("--data_dir") + 1])
    diagnostic_paths = next(iter(diagnostic_data.values()))
    assert set(diagnostic_paths) == {"base", "mesh_dump", "dual_grid"}
    assert diagnostic[-2:] == ["--auto_retry", "0"]
    scale_probe = e12_controlled_scale_command(
        "toothfairy-stage1-v1", "stage1-e12-g1-controlled-scale12-v1"
    )
    scale_data = json.loads(scale_probe[scale_probe.index("--data_dir") + 1])
    scale_paths = next(iter(scale_data.values()))
    assert set(scale_paths) == {"base", "mesh_dump", "dual_grid"}
    assert scale_probe[-2:] == ["--auto_retry", "0"]
    e15 = e15_regional_decoder_command(
        "toothfairy-stage1-v1", "stage1-e15-regional-decoder-zero-step-v2"
    )
    e15_data = json.loads(e15[e15.index("--data_dir") + 1])
    e15_paths = next(iter(e15_data.values()))
    assert set(e15_paths) == {"base", "mesh_dump", "dual_grid"}
    assert all("e12_g1_one_tooth_v6" in path for path in e15_paths.values())
    assert e15[-2:] == ["--auto_retry", "0"]


def test_training_seed_patch_is_explicit_and_fail_closed():
    source = "def main(rank):\n    setup_rng(rank)\n"
    patched = training_entry_source_with_experiment_seed(source, 1724708096)
    assert "setup_rng(rank + 1724708096)" in patched
    try:
        training_entry_source_with_experiment_seed("def main(): pass\n", 1)
    except ValueError as error:
        assert "RNG setup changed" in str(error)
    else:
        raise AssertionError("Expected changed upstream RNG source to fail closed")


def test_stage1_validation_requires_paired_improvement_and_non_regression():
    regions = {
        name: {
            "available": True,
            "symmetricChamferPercentDiagonal": 0.2,
            "hausdorff95PercentDiagonal": 0.3,
            "surfaceFscoreAt2Percent": 0.9,
            "sampleShareAbsoluteError": 0.01,
        }
        for name in ("apicalRootProxy", "middleRootProxy", "cervicalProxy", "crownProxy")
    }
    topology = {
        "coincidentVertexWeldedTopology": {
            "componentCount": 1,
            "largestComponentAreaFraction": 1.0,
            "boundaryEdgeCount": 0,
            "nonManifoldEdgeCount": 0,
        }
    }
    base, candidate = [], []
    families = ("incisor", "canine", "premolar", "molar")
    for index in range(12):
        common = {
            "id": f"case-{index}",
            "toothFamily": families[index % 4],
            "topology": topology,
            "repeatability": {"geometricallyStable": True} if index < 4 else None,
        }
        axial = {
            "regions": regions,
            "robustPoleProxyErrorsPercentDiagonal": {"apical": 0.1, "coronal": 0.1},
        }
        base.append({**common, "metrics": {
            "symmetricChamferPercentDiagonal": 1.0,
            "hausdorff95PercentDiagonal": 1.0,
            "surfaceFscoreAt2Percent": 0.8,
            "sortedExtentRelativeError": 0.1,
            "canonicalAxialAnatomyProxy": axial,
        }})
        candidate.append({**common, "metrics": {
            "symmetricChamferPercentDiagonal": 0.9,
            "hausdorff95PercentDiagonal": 0.95,
            "surfaceFscoreAt2Percent": 0.85,
            "sortedExtentRelativeError": 0.09,
            "canonicalAxialAnatomyProxy": axial,
        }})
    result = summarize_stage1_validation(base, candidate)
    assert result["passed"] is True
    assert result["medianPairedChamferRelativeImprovement"] >= 0.05
    assert result["repeatability"]["criterion"] == "normalized-surface-repeatability-v1"


def test_trust_region_trainer_patch_is_fail_closed_and_uses_master_params():
    source = (
        "class BasicTrainer:\n"
        "    def __init__(self, finetune_ckpt=None, **kwargs):\n"
        "        elif finetune_ckpt is not None:\n"
        "            self.finetune_from(finetune_ckpt)\n"
        "\n"
        "    def run_step(self):\n"
        "        step_log = {'loss': {}, 'status': {}}\n"
        "        amp_context = partial(torch.autocast, device_type='cuda', dtype=self.mix_precision_dtype) if self.mix_precision_mode == 'amp' else nullcontext\n"
        "        elastic_controller_context = self.elastic_controller.record if self.elastic_controller_config is not None else nullcontext\n"
        "        ## adjust learning rate\n"
    )
    patched = trust_region_trainer_source(source)
    assert "dentalsculptor_anchor_params" in patched
    assert "trust_region_relative_l2_after" in patched
    assert "master_params_to_model_params" in patched
    assert "self.mix_precision_mode in ('amp', 'inflat_all')" in patched
    assert patched.count("## adjust learning rate") == 1


def test_trust_region_trainer_patch_rejects_unknown_upstream_source():
    try:
        trust_region_trainer_source("class BasicTrainer: pass\n")
    except ValueError as error:
        assert "refusing trust-region patch" in str(error)
    else:
        raise AssertionError("Expected an unknown trainer source to be rejected")


def test_teacher_consistency_patch_is_explicit_and_fail_closed():
    source = (
        "class FlowMatchingTrainer:\n"
        "    def __init__(self, *args, t_schedule=None, **kwargs):\n"
        "        super().__init__(*args, **kwargs)\n"
        "        self.t_schedule = t_schedule\n"
        "    def training_losses(self, x_0, cond=None, **kwargs):\n"
        "        pred = self.training_models['denoiser'](x_t, t * 1000, cond, **kwargs)\n"
        "        assert pred.shape == noise.shape == x_0.shape\n"
        "        terms[\"mse\"] = F.mse_loss(pred, target)\n"
        "        terms[\"loss\"] = terms[\"mse\"]\n"
    )
    patched = teacher_consistency_flow_source(source)
    assert "copy.deepcopy" in patched
    assert ".eval().requires_grad_(False)" in patched
    assert "teacher_consistency_mse" in patched
    assert "with torch.no_grad()" in patched

    try:
        teacher_consistency_flow_source("class FlowMatchingTrainer: pass\n")
    except ValueError as error:
        assert "refusing teacher patch" in str(error)
    else:
        raise AssertionError("Expected an unknown flow trainer source to be rejected")


def test_calibrated_teacher_patch_is_bounded_detached_and_fail_closed():
    source = (
        "class FlowMatchingTrainer:\n"
        "    def __init__(self, *args, t_schedule=None, **kwargs):\n"
        "        super().__init__(*args, **kwargs)\n"
        "        self.t_schedule = t_schedule\n"
        "    def training_losses(self, x_0, cond=None, **kwargs):\n"
        "        pred = self.training_models['denoiser'](x_t, t * 1000, cond, **kwargs)\n"
        "        assert pred.shape == noise.shape == x_0.shape\n"
        "        terms[\"mse\"] = F.mse_loss(pred, target)\n"
        "        terms[\"loss\"] = terms[\"mse\"]\n"
    )
    patched = calibrated_teacher_consistency_flow_source(source)
    assert "copy.deepcopy" in patched
    assert "target ratio must be in (0, 0.25]" in patched
    assert "teacher_consistency_mse\"].detach().clamp_min" in patched
    assert "dentalsculptor_consistency_scale_max" in patched
    assert "teacher_consistency_share" in patched
    try:
        calibrated_teacher_consistency_flow_source("class FlowMatchingTrainer: pass\n")
    except ValueError as error:
        assert "refusing calibrated teacher patch" in str(error)
    else:
        raise AssertionError("Expected changed upstream flow source to fail closed")


def test_axial_band_shape_objective_is_balanced_and_fail_closed():
    source = (
        "class FlowMatchingTrainer:\n"
        "    def __init__(self, *args, t_schedule=None, **kwargs):\n"
        "        super().__init__(*args, **kwargs)\n"
        "        self.t_schedule = t_schedule\n"
        "    def training_losses(self, x_0, cond=None, **kwargs):\n"
        "        pred = self.training_models['denoiser'](x_t, t * 1000, cond, **kwargs)\n"
        "        assert pred.shape == noise.shape == x_0.shape\n"
        "        terms[\"mse\"] = F.mse_loss(pred, target)\n"
        "        terms[\"loss\"] = terms[\"mse\"]\n"
    )
    patched = axial_band_balanced_teacher_shape_flow_source(source)
    assert "dentalsculptor_axial_band_count != 4" in patched
    assert "principal_axis = int(torch.argmax(spans).item())" in patched
    assert "torch.stack(band_losses).mean()" in patched
    assert "dentalsculptor_teacher_target_ratio != 0.05" in patched
    assert "terms[\"loss\"] = axial_mse + teacher_contribution" in patched
    try:
        axial_band_balanced_teacher_shape_flow_source("class FlowMatchingTrainer: pass\n")
    except ValueError as error:
        assert "refusing axial patch" in str(error)
    else:
        raise AssertionError("Expected changed upstream shape-flow source to fail closed")


def test_e10_patches_effective_sparse_override_and_parent_init():
    parent = (
        "class FlowMatchingTrainer:\n"
        "    def __init__(self, *args, t_schedule=None, **kwargs):\n"
        "        super().__init__(*args, **kwargs)\n"
        "        self.t_schedule = t_schedule\n"
    )
    sparse = (
        "class SparseFlowMatchingTrainer(FlowMatchingTrainer):\n"
        "    def training_losses(self, x_0, cond=None, **kwargs):\n"
        "        pred = self.training_models['denoiser'](x_t, t * 1000, cond, **kwargs)\n"
        "        assert pred.shape == noise.shape == x_0.shape\n"
        "        target = self.get_v(x_0, noise, t)\n"
        "        terms[\"mse\"] = F.mse_loss(pred.feats, target.feats)\n"
        "        terms[\"loss\"] = terms[\"mse\"]\n"
    )
    patched_parent = e10_teacher_init_flow_source(parent)
    patched_sparse = e10_axial_sparse_flow_source(sparse)
    assert "self.dentalsculptor_teacher = copy.deepcopy" in patched_parent
    assert "DENTALSCULPTOR_E10_OBJECTIVE_RECEIPT" in patched_sparse
    assert "effectiveTrainerClass" in patched_sparse
    assert "terms[\"loss\"] = axial_mse + teacher_contribution" in patched_sparse
    for patcher in (e10_teacher_init_flow_source, e10_axial_sparse_flow_source):
        try:
            patcher("class ChangedUpstream: pass\n")
        except ValueError:
            pass
        else:
            raise AssertionError("Expected changed upstream source to fail closed")


def test_e10_post_update_probe_is_read_only_and_fail_closed():
    source = (
        "class BasicTrainer:\n"
        "    def run_step(self, data_list):\n"
        "        ## adjust learning rate\n"
        "        if self.lr_scheduler_config is not None:\n"
        "            self.lr_scheduler.step()\n"
    )
    patched = e10_post_update_probe_trainer_source(source)
    assert "torch.no_grad()" in patched
    assert "post_update_probe" in patched
    assert "self.training_losses(**data_list[0])" in patched
    probe = patched[patched.index("DentalSculptor read-only"):patched.index("## adjust learning rate", patched.index("DentalSculptor read-only"))]
    assert ".backward(" not in probe
    assert "optimizer.step(" not in probe
    try:
        e10_post_update_probe_trainer_source("class Changed: pass\n")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected changed optimizer boundary to fail closed")


def test_r04b_basic_probe_seals_after_backward_and_before_optimizer():
    source = (
        "import os\nimport json\nimport torch\n"
        "class BasicTrainer:\n"
        "    def run_step(self, data_list):\n"
        "        losses = []\n"
        "        l.backward()\n"
        "        ## gradient clip\n"
        "        if self.grad_clip is not None:\n"
        "            pass\n"
        "        ## step\n"
        "        self.optimizer.step()\n"
    )
    patched = r04b_basic_zero_step_probe_source(source)
    assert "parameter.grad" in patched
    assert "BasicTrainer.run_step.after-effective-backward-before-gradient-clip" in patched
    assert patched.index("l.backward()") < patched.index("DENTALSCULPTOR_R04B_ZERO_STEP_COMPLETE")
    assert patched.index("DENTALSCULPTOR_R04B_ZERO_STEP_COMPLETE") < patched.index("self.optimizer.step()")
    assert "torch.autograd.grad" not in patched
    try:
        r04b_basic_zero_step_probe_source("class ChangedBasicTrainer: pass\n")
    except ValueError as error:
        assert "refusing R0.4B probe patch" in str(error)
    else:
        raise AssertionError("Expected changed BasicTrainer source to fail closed")


def test_r04c_adapter_optimizer_is_isolated_and_one_step_probe_is_ordered():
    parent = (
        "import torch\n"
        "class FlowMatchingTrainer:\n"
        "    def __init__(self, *args, t_schedule=None, **kwargs):\n"
        "        super().__init__(*args, **kwargs)\n"
        "        self.t_schedule = t_schedule\n"
    )
    installed = r04c_install_trainable_adapter_flow_source(parent)
    assert "self.model_params = adapter_parameters" in installed
    assert "torch.optim.AdamW(adapter_parameters, lr=1e-6" in installed
    assert "weight_decay=0.0" in installed

    basic = (
        "class BasicTrainer:\n"
        "    def run_step(self):\n"
        "        self.optimizer.step()\n"
        "        ## adjust learning rate\n"
        "        if self.lr_scheduler_config is not None:\n"
        "            pass\n"
    )
    patched = r04c_basic_one_step_probe_source(basic)
    marker = patched.index("DENTALSCULPTOR_R04C_ONE_STEP_COMPLETE")
    assert patched.index("self.optimizer.step()") < marker
    assert marker < patched.index("## adjust learning rate")
    assert "candidate-sparse-flow" not in patched
    assert "torch.save(merged, checkpoint_path)" in patched
    assert "adapter.base.weight.detach().float()" in patched
    for bad in ("class Changed: pass\n", basic.replace("## adjust learning rate", "## changed")):
        try:
            r04c_basic_one_step_probe_source(bad)
        except ValueError:
            pass
        else:
            raise AssertionError("Expected changed BasicTrainer source to fail closed")


def test_r05a_integrates_decoded_regional_terms_and_stops_before_update():
    parent = """import torch
class Flow:
    def __init__(self, *args, t_schedule=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.t_schedule = t_schedule
    def training_losses(self, x_0, cond=None, **kwargs):
        pred = self.training_models['denoiser'](x_t, t * 1000, cond, **kwargs)
        target = self.get_v(x_0, noise, t)
        terms = {}
        terms[\"mse\"] = F.mse_loss(pred, target)
        terms[\"loss\"] = terms[\"mse\"]
        return terms, {}
"""
    installed = r05a_install_adapter_flow_source(parent)
    assert "dentalsculptor_adapter_enabled" in installed
    objective = r05a_regional_objective_sparse_loss_source(installed)
    for marker in (
        "crown_positive_bce", "crown_extra_bce", "non_crown_teacher_mse",
        "non_crown_teacher_probe", "self.dataset._loading_ss_dec()", "support_union",
        "occupied_indices", "spatial_bounds", "axialSpatialOffset",
        "crownDirection", "lowerTerminalReferenceVoxelCount",
    ):
        assert marker in objective
    assert "candidate_logits.shape[-1] * 0.72" not in objective
    assert "normalized_axial >= 0.72" in objective
    assert "0.5 * crown_positive_bce" in objective
    assert "0.05 * non_crown_teacher" in objective

    basic = """def run_step(self):
        ## gradient clip
        if self.grad_clip is not None:
            pass
        self.optimizer.step()
"""
    patched = r05a_basic_zero_step_probe_source(basic)
    assert patched.index("DENTALSCULPTOR_R05A_ZERO_STEP_COMPLETE") < patched.index("self.optimizer.step()")
    assert "optimizerSteps': 0" in patched


def test_r05b_executes_exactly_one_regional_adapter_step_and_seals_checkpoint():
    parent = """import torch
class Flow:
    def __init__(self, *args, t_schedule=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.t_schedule = t_schedule
"""
    installed = r05b_install_trainable_adapter_flow_source(parent)
    assert "dentalsculptor_adapter_enabled" in installed
    assert "torch.optim.AdamW(adapter_parameters, lr=1e-6" in installed
    assert "dentalsculptor_r05b_adapter_initial" in installed

    basic = """def run_step(self):
        self.optimizer.step()
        ## adjust learning rate
        if self.lr_scheduler_config is not None:
            pass
"""
    patched = r05b_basic_one_step_probe_source(basic)
    marker = patched.index("DENTALSCULPTOR_R05B_ONE_STEP_COMPLETE")
    assert patched.index("self.optimizer.step()") < marker
    assert marker < patched.index("## adjust learning rate")
    assert "self.dentalsculptor_r05a_objective_receipt" in patched
    assert "torch.save(merged, checkpoint_path)" in patched


def test_e10_one_tooth_command_is_sealed_and_disables_retry():
    command = e10_one_tooth_training_command(
        "toothfairy-stage1-v1", "stage1-e10-g1-one-tooth-v1"
    )
    assert command[command.index("--auto_retry") + 1] == "0"
    data_spec = json.loads(command[command.index("--data_dir") + 1])
    only = next(iter(data_spec.values()))
    assert only["base"].endswith("/e10_g1_one_tooth_v1/base")
    assert only["shape_latent"].endswith("/e10_g1_one_tooth_v1/shape_latent")
    try:
        e10_one_tooth_training_command("wrong-dataset", "valid-name")
    except ValueError as error:
        assert "sealed" in str(error)
    else:
        raise AssertionError("Expected unregistered E10 dataset to fail closed")


def test_sparse_anchor_command_uses_only_sealed_anchor_view():
    command = sparse_anchor_training_command("toothfairy-tf-pw32-v1", "e7-smoke")
    spec = json.loads(command[command.index("--data_dir") + 1])
    roots = spec["toothfairy-tf-pw32-v1-anchor8"]
    assert set(roots) == {"base", "ss_latent", "render_cond"}
    assert all("sparse_anchor_v1" in path for path in roots.values())
    assert command[command.index("--auto_retry") + 1] == "0"


def test_decoded_occupancy_patch_targets_inference_boundary_and_fails_closed():
    source = (
        "from ...utils.general_utils import dict_reduce\n"
        "class FlowMatchingTrainer:\n"
        "    def __init__(self, *args, t_schedule=None, **kwargs):\n"
        "        super().__init__(*args, **kwargs)\n"
        "        self.t_schedule = t_schedule\n"
        "    def training_losses(self, x_0, cond=None, **kwargs):\n"
        "        terms[\"mse\"] = F.mse_loss(pred, target)\n"
        "        terms[\"loss\"] = terms[\"mse\"]\n"
    )
    patched = decoded_occupancy_flow_source(source)
    assert "from ... import models" in patched
    assert ".eval().requires_grad_(False)" in patched
    assert "student_x0 = (1 - self.sigma_min) * noise - pred" in patched
    assert "target_occupancy = (target_logits > 0).float()" in patched
    assert "binary_cross_entropy_with_logits" in patched
    assert "occupancy_dice" in patched
    assert "occupancy_raw.detach().clamp_min" in patched
    try:
        decoded_occupancy_flow_source("class FlowMatchingTrainer: pass\n")
    except ValueError as error:
        assert "refusing occupancy patch" in str(error)
    else:
        raise AssertionError("Expected changed upstream flow source to fail closed")


def test_e9_gradient_diagnostic_is_sealed_zero_update_and_fail_closed():
    source = (
        "from ...utils.general_utils import dict_reduce\n"
        "class FlowMatchingTrainer:\n"
        "    def __init__(self, *args, t_schedule=None, **kwargs):\n"
        "        super().__init__(*args, **kwargs)\n"
        "        self.t_schedule = t_schedule\n"
        "    def training_losses(self, x_0, cond=None, **kwargs):\n"
        "        t = self.sample_t(x_0.shape[0]).to(x_0.device).float()\n"
        "        terms[\"mse\"] = F.mse_loss(pred, target)\n"
        "        terms[\"loss\"] = terms[\"mse\"]\n"
    )
    patched = e9_gradient_diagnostic_flow_source(source)
    assert "expected = [0.05, 0.25, 0.5, 0.75, 0.95]" in patched
    assert "torch.autograd.grad" in patched
    assert "gradient_cosine_similarity" in patched
    assert "occupancy_to_mse_gradient_norm_ratio" in patched
    assert 'terms["loss"] = terms["mse"]' in patched
    assert "occupancy_contribution" not in patched
    try:
        e9_gradient_diagnostic_flow_source("class FlowMatchingTrainer: pass\n")
    except ValueError as error:
        assert "refusing E9 diagnostic patch" in str(error)
    else:
        raise AssertionError("Expected changed upstream E9 source to fail closed")


def test_e9_family_command_is_isolated_and_rejects_unknown_family():
    command = e9_family_diagnostic_command("toothfairy-tf-pw32-v1", "incisor", "e9-test")
    spec = json.loads(command[command.index("--data_dir") + 1])
    roots = next(iter(spec.values()))
    assert all("e9_gradient_views_v3/incisor" in path for path in roots.values())
    assert command[command.index("--auto_retry") + 1] == "0"
    try:
        e9_family_diagnostic_command("toothfairy-tf-pw32-v1", "unknown", "e9-test")
    except ValueError as error:
        assert "Unsupported E9 tooth family" in str(error)
    else:
        raise AssertionError("Expected unknown E9 family to be rejected")


def test_mixed_representation_ceiling_selection_is_source_and_scope_aware():
    families = ("incisor", "canine", "premolar", "molar")
    toothfairy = {
        "datasetId": "toothfairy-tf-pw32-v1",
        "assets": [{
            "id": f"tf-{family}", "canonicalSha256": f"{index:064x}",
            "canonicalPath": f"tf-{family}.ply", "groupId": f"patient-{index}",
            "split": "train", "toothFamily": family,
            "representationScope": "whole-tooth", "rootSupervision": True,
        } for index, family in enumerate(families, start=1)],
    }
    crown_assets = []
    for index, family in enumerate(families, start=10):
        crown_assets.append({
            "id": f"t3-{family}", "canonicalSha256": f"{index:064x}",
            "canonicalPath": f"t3-{family}.ply", "groupId": f"patient-{index}",
            "split": "train", "toothFamily": family,
            "originDatasetId": "teeth3ds-pilot-v1", "fdiNumber": 11,
        })
    for index in range(20, 24):
        crown_assets.append({
            "id": f"dtu-{index}", "canonicalSha256": f"{index:064x}",
            "canonicalPath": f"dtu-{index}.ply", "groupId": f"scan-{index}",
            "split": "train", "toothFamily": "molar",
            "originDatasetId": "fdi16-pilot-v1", "fdiNumber": 16,
        })
    selected = select_mixed_representation_ceiling_cases(
        toothfairy, {"datasetId": "dental-anatomy-v1", "assets": crown_assets}
    )
    assert len(selected) == 12
    assert [row["ceilingSource"] for row in selected].count("toothfairy2") == 4
    assert [row["ceilingSource"] for row in selected].count("teeth3ds") == 4
    assert [row["ceilingSource"] for row in selected].count("dtu-fdi16") == 4
    assert all(row["rootSupervision"] for row in selected[:4])
    assert not any(row["rootSupervision"] for row in selected[4:])


def test_mixed_representation_ceiling_rejects_missing_family():
    try:
        select_mixed_representation_ceiling_cases(
            {"datasetId": "toothfairy-tf-pw32-v1", "assets": []},
            {"datasetId": "dental-anatomy-v1", "assets": []},
        )
    except ValueError as error:
        assert "whole-tooth incisor" in str(error)
    else:
        raise AssertionError("Expected incomplete mixed ceiling cohort to fail closed")


def test_mixed_ceiling_cleanup_is_evaluation_only_and_fail_closed():
    source = (Path(__file__).parents[1] / "modal_app" / "train_anatomy.py").read_text(
        encoding="utf-8"
    )
    body = source[
        source.index("def qualify_mixed_ceiling_main_components"):
        source.index("def compare_e1_trial_geometry")
    ]
    assert "area_fraction >= 0.99" in body
    assert '"minimumCleanedSurfaceFscoreAt2Percent": 0.99' in body
    assert '"cleanupIsEvaluationOnly": True' in body
    assert '"trainingExecuted": False' in body
    assert '"productionPromotionPermitted": False' in body


def test_occupancy_screen_always_checks_base_and_candidate_repeatability():
    source = (Path(__file__).parents[1] / "modal_app" / "train_anatomy.py").read_text(
        encoding="utf-8"
    )
    assert '"baseRepeatability": base_repeatability' in source
    assert '"candidateRepeatability": candidate_repeatability' in source
    assert '"benchmarkValid": base_exactly_repeatable and candidate_exactly_repeatable' in source
    assert 'dataset_root / "frozen_sparse_base_v1"' in source
    assert 'np.load(path, allow_pickle=False)' in source
    assert '"frozenBaseCohortSha256": frozen_receipt["cohortSha256"]' in source
    assert "if all_families_passed:" not in source[source.index("def screen_sparse_canary_occupancy"):source.index("def validate_training_runtime")]


def test_frozen_sparse_base_is_fail_closed_and_content_addressed():
    source = (Path(__file__).parents[1] / "modal_app" / "train_anatomy.py").read_text(
        encoding="utf-8"
    )
    body = source[
        source.index("def freeze_sparse_base_benchmark"):
        source.index("def validate_training_runtime")
    ]
    assert "benchmarkInputsSha256" in body
    assert "exactlyRepeatableEveryFamily" in body
    assert "Base sparse benchmark is not exactly repeatable; nothing persisted" in body
    assert "allow_pickle=False" in body
    assert "cohortSha256" in body
    assert '"trainingExecuted": False' in body
    assert '"productionMutationPermitted": False' in body


def test_sparse_occupancy_metrics_measure_disconnected_components():
    coords = [[0, 1, 1, 1], [0, 1, 1, 2], [0, 6, 6, 6]]
    result = sparse_occupancy_metrics(coords, resolution=8)
    assert result["voxelCount"] == 3
    assert result["componentCount6Connected"] == 2
    assert result["largestComponentVoxelFraction"] == 2 / 3
    assert result["boundsExtent"] == [6, 6, 6]


def test_sparse_occupancy_comparison_is_exact_and_directional():
    base = [[0, 0, 0], [0, 0, 1], [0, 1, 1]]
    candidate = [[0, 0, 0], [0, 0, 1], [1, 1, 1], [2, 2, 2]]
    result = compare_sparse_occupancies(base, candidate, resolution=4)
    assert result["intersectionVoxelCount"] == 2
    assert result["unionVoxelCount"] == 5
    assert result["voxelIoU"] == 0.4
    assert result["addedVoxelCount"] == 2
    assert result["removedVoxelCount"] == 1
    assert not result["exactlyEqual"]


def test_sparse_occupancy_rejects_multiple_batches():
    try:
        sparse_occupancy_metrics([[0, 1, 1, 1], [1, 1, 1, 2]], resolution=8)
    except ValueError as error:
        assert "exactly one" in str(error)
    else:
        raise AssertionError("Expected multiple sparse batches to be rejected")


def test_sparse_task_vector_interpolation_scales_update_and_preserves_derived_buffer():
    import numpy as np

    class TensorStub:
        def __init__(self, values, dtype=None):
            self.values = np.asarray(values, dtype=dtype)
            self.shape = self.values.shape
            self.dtype = self.values.dtype
        def detach(self): return self
        def clone(self): return TensorStub(self.values.copy())
        def float(self): return TensorStub(self.values.astype(np.float32))
        def sub(self, other): return TensorStub(self.values - other.values)
        def add(self, other, alpha=1.0): return TensorStub(self.values + alpha * other.values)
        def to(self, *, dtype): return TensorStub(self.values.astype(dtype))
        def is_floating_point(self): return np.issubdtype(self.dtype, np.floating)
        def equal(self, other): return np.array_equal(self.values, other.values)

    base = {"weight": TensorStub([0.0, 2.0]), "counter": TensorStub([3])}
    candidate = {
        "weight": TensorStub([2.0, 4.0]),
        "counter": TensorStub([3]),
        "rope_phases": TensorStub([7.0]),
    }
    result = interpolate_sparse_task_vector(base, candidate, 0.25)
    assert np.array_equal(result["weight"].values, [0.5, 2.5])
    assert result["counter"].equal(candidate["counter"])
    assert result["rope_phases"].equal(candidate["rope_phases"])


def test_sparse_task_vector_interpolation_fails_closed_on_schema_drift():
    try:
        interpolate_sparse_task_vector(
            {"weight": object()},
            {"other": object()},
            0.1,
        )
    except ValueError as error:
        assert "schema mismatch" in str(error)
    else:
        raise AssertionError("Expected checkpoint schema drift to be rejected")


def test_preprocess_image_declares_blender_runtime_libraries():
    source = Path(__file__).parents[1] / "modal_app" / "train_anatomy.py"
    text = source.read_text(encoding="utf-8")
    for package in ("libxrender1", "libxi6", "libxkbcommon-x11-0", "libsm6", "libxfixes3", "libgl1"):
        assert f'"{package}"' in text


def test_training_command_is_pinned_and_shape_only():
    command = training_command("dental_anatomy_v1", "fdi16_spike_v1")
    data_spec = json.loads(command[command.index("--data_dir") + 1])
    roots = data_spec["dental_anatomy_v1"]
    assert roots["base"].endswith("/training_views/train")
    assert set(roots) == {"base", "shape_latent", "render_cond"}
    joined = " ".join(command)
    assert "dentalsculptor_finetune_config.json" in joined
    assert "imgshape2tex" not in joined
    assert "/datasets/dental_anatomy_v1" in joined
    assert "/checkpoints/fdi16_spike_v1" in joined
    assert FDI16_URL.endswith("44571158")
    assert FDI16_MD5 == "9824c7d342f6f13887084452d2c75c68"
    assert len(TRAINING_CODE_COMMIT) == 40
    assert BASE_SHAPE_FLOW_FILE.endswith("slat_flow_img2shape_dit_1_3B_512_bf16")


def test_finetune_config_loads_base_and_uses_bounded_schedule():
    source = {
        "trainer": {
            "args": {
                "max_steps": 1_000_000,
                "optimizer": {"name": "AdamW", "args": {"lr": 1e-4}},
            }
        }
    }
    result = build_finetune_config(source, "/pinned/base", max_steps=12_000)
    args = result["trainer"]["args"]
    assert args["finetune_ckpt"] == {"denoiser": "/pinned/base"}
    assert args["max_steps"] == 12_000
    assert args["optimizer"]["args"]["lr"] == 1e-5
    assert args["i_save"] == 1_000
    assert "finetune_ckpt" not in source["trainer"]["args"]


def test_smoke_command_uses_isolated_balanced_view():
    command = smoke_training_command("dental-anatomy-v1", "smoke-v1")
    spec = json.loads(command[command.index("--data_dir") + 1])
    roots = spec["dental-anatomy-v1-smoke"]
    assert all("smoke_training_v1" in path for path in roots.values())
    assert command[command.index("--auto_retry") + 1] == "0"


def test_smoke_preparation_writes_required_shape_token_contract():
    source = (Path(__file__).parents[1] / "modal_app" / "train_anatomy.py").read_text(encoding="utf-8")
    assert '"shape_latent_tokens"' in source
    assert 'packed_latent["coords"].shape[0]' in source
    assert '"shapeLatentTokens": int(row["shape_latent_tokens"])' in source


def test_trainer_checkpoint_adapter_rejects_non_safetensors(tmp_path):
    wrong = tmp_path / "base.pt"
    wrong.write_bytes(b"not a checkpoint")
    try:
        materialize_trainer_checkpoint(str(wrong), tmp_path / "converted.pt")
    except FileNotFoundError as error:
        assert "safetensors" in str(error)
    else:
        raise AssertionError("Expected a non-safetensors checkpoint to be rejected")


def test_smoke_patch_disables_only_unconditional_visualizations():
    source = """        if self.is_master:
            self.snapshot_dataset(batch_size=self.snapshot_batch_size)
        if self.step == 0:
            self.snapshot(suffix='init', batch_size=self.snapshot_batch_size)
        else: # resume
            self.snapshot(suffix=f'resume_step{self.step:07d}', batch_size=self.snapshot_batch_size)
        self.snapshot(suffix='final', batch_size=self.snapshot_batch_size)
"""
    patched = smoke_trainer_source_without_snapshots(source)
    assert "snapshot(" not in patched
    assert patched.count("DentalSculptor smoke") == 4


def test_smoke_patch_fails_closed_if_pinned_trainer_changes():
    try:
        smoke_trainer_source_without_snapshots("def run(self): pass")
    except ValueError as error:
        assert "snapshot statement changed" in str(error)
    else:
        raise AssertionError("Expected changed upstream trainer source to fail closed")


def test_sparse_flow_patch_restores_only_config_derived_rope_buffer():
    source = """                model_ckpts[name] = model_ckpt
                model.load_state_dict(model_ckpt)
"""
    patched = sparse_flow_trainer_source_with_derived_rope_buffer(source)
    assert "missing_keys != {'rope_phases'}" in patched
    assert "model_state_dict['rope_phases']" in patched
    assert "load_state_dict(model_ckpt, strict=True)" in patched


def test_sparse_flow_patch_fails_closed_if_upstream_loader_changes():
    try:
        sparse_flow_trainer_source_with_derived_rope_buffer("model.load_state_dict(model_ckpt, strict=False)")
    except ValueError as error:
        assert "refusing compatibility patch" in str(error)
    else:
        raise AssertionError("Expected changed upstream trainer source to fail closed")


def test_finite_loss_parser_rejects_non_numeric_and_reads_scientific_values():
    assert finite_losses_from_log("step 1 loss: 1.25 step 2 'loss': 4.5e-2") == [1.25, 0.045]
    assert finite_losses_from_log("loss: nan loss: inf") == []


def test_canonical_training_log_parser_reads_only_step_losses():
    text = (
        '1: {"loss": {"bin_1": {"mse": 9.0}, "loss": 0.42}}\n'
        '2: {"loss": {"loss": 5.1e-1}, "status": {"grad_norm": 0.2}}\n'
    )
    assert finite_losses_from_training_log(text) == [0.42, 0.51]


def test_e3_gate_rejects_regional_or_welded_topology_regression():
    regions = {
        name: {
            "available": True,
            "symmetricChamferPercentDiagonal": 1.0,
            "hausdorff95PercentDiagonal": 2.0,
            "surfaceFscoreAt2Percent": 0.8,
            "sampleShareAbsoluteError": 0.01,
        }
        for name in ("apicalRootProxy", "middleRootProxy", "cervicalProxy", "crownProxy")
    }
    metrics = {"canonicalAxialAnatomyProxy": {
        "regions": regions,
        "robustPoleProxyErrorsPercentDiagonal": {"apical": 1.0, "coronal": 1.0},
    }}
    topology = {"coincidentVertexWeldedTopology": {
        "componentCount": 2,
        "largestComponentAreaFraction": 0.99,
        "boundaryEdgeCount": 10,
        "nonManifoldEdgeCount": 2,
    }}
    baseline = [{"id": "molar", "toothFamily": "molar", "metrics": metrics, "topology": topology}]
    candidate_metrics = json.loads(json.dumps(metrics))
    candidate_metrics["canonicalAxialAnatomyProxy"]["regions"]["crownProxy"][
        "symmetricChamferPercentDiagonal"
    ] = 1.5
    candidate_topology = json.loads(json.dumps(topology))
    candidate_topology["coincidentVertexWeldedTopology"]["componentCount"] = 3
    result = evaluate_e3_engineering_gates(baseline, [{
        "id": "molar", "toothFamily": "molar",
        "metrics": candidate_metrics, "topology": candidate_topology,
    }])
    assert not result["passed"]
    assert any("crownProxy" in reason for reason in result["reasons"])
    assert any("componentCount" in reason for reason in result["reasons"])


def test_training_metadata_view_contains_only_train_rows(tmp_path):
    import numpy as np

    fields = ["sha256", "split", "shape_latent_encoded", "cond_rendered"]
    rows = [
        {"sha256": "a" * 64, "split": "train", "shape_latent_encoded": "True", "cond_rendered": "True"},
        {"sha256": "b" * 64, "split": "validation", "shape_latent_encoded": "True", "cond_rendered": "True"},
        {"sha256": "c" * 64, "split": "test", "shape_latent_encoded": "True", "cond_rendered": "True"},
    ]
    with (tmp_path / "metadata.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    latent = tmp_path / "shape_latents" / "shape_enc_next_dc_f16c32_fp16_512"
    latent.mkdir(parents=True)
    np.savez(latent / f"{'a' * 64}.npz", coords=np.zeros((3, 3), dtype=np.int32))
    (tmp_path / "renders_cond" / ("a" * 64)).mkdir(parents=True)

    result = prepare_training_metadata_view(tmp_path, 512)
    assert result["trainCount"] == 1
    assert result["uniqueTrainHashes"] == 1
    for path in result["metadataPaths"]:
        with open(path, newline="", encoding="utf-8") as stream:
            filtered = list(csv.DictReader(stream))
        assert [row["sha256"] for row in filtered] == ["a" * 64]


def test_candidate_comparison_is_direction_aware_and_never_promotes():
    metrics = {
        "symmetricChamferPercentDiagonal": 4.0,
        "hausdorff95PercentDiagonal": 8.0,
        "surfaceFscoreAt2Percent": 0.2,
        "sortedExtentRelativeError": 0.3,
    }
    baseline = [{"id": "a", "toothFamily": "molar", "metrics": metrics}]
    candidate_metrics = dict(metrics)
    candidate_metrics.update({
        "symmetricChamferPercentDiagonal": 3.5,
        "hausdorff95PercentDiagonal": 8.1,
        "surfaceFscoreAt2Percent": 0.25,
        "sortedExtentRelativeError": 0.29,
    })
    candidate = [{"id": "a", "toothFamily": "molar", "metrics": candidate_metrics}]
    result = summarize_candidate_comparison(baseline, candidate)
    assert result["preliminaryScreenPassed"] is True
    assert result["productionPromotionPermitted"] is False
    assert result["clinicalClaimPermitted"] is False
    assert result["aggregate"]["symmetricChamferPercentDiagonal"]["improved"] is True
    assert result["aggregate"]["surfaceFscoreAt2Percent"]["improved"] is True


def test_e1_trials_are_immutable_and_named():
    source = (Path(__file__).parents[1] / "modal_app" / "train_anatomy.py").read_text(encoding="utf-8")
    assert 'trial_id: str = "trial-1"' in source
    assert "Immutable E1 trial already exists" in source
    assert '"trialId": trial_id' in source
