package com.mrpeel.cricketbattingtracker.ml

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File
import kotlin.math.abs

@Suppress("UNCHECKED_CAST")
class Stage3RuleEngineParityTest {

    private fun loadParityResourceMap(): Map<String, Any?> {
        val stream = javaClass.classLoader?.getResourceAsStream("stage3_parity_vectors.json")
        assertNotNull("stage3_parity_vectors.json must exist in test resources", stream)
        val text = stream!!.bufferedReader(Charsets.UTF_8).use { it.readText() }
        return Stage3RuleEngine.parseSimpleJsonMap(text)
    }

    @Test
    fun `shared JSON config in assets matches pipelines stage3_rules_config json`() {
        val candidates = listOf(
            File("src/main/assets/models/stage3_rules_config.json") to File("../pipelines/stage3_rules_config.json"),
            File("app/src/main/assets/models/stage3_rules_config.json") to File("pipelines/stage3_rules_config.json")
        )
        val pair = candidates.firstOrNull { it.first.exists() && it.second.exists() }
        assertNotNull("Both asset and pipeline stage3_rules_config.json files must exist", pair)
        val assetText = pair!!.first.readText(Charsets.UTF_8).trim()
        val pipelineText = pair.second.readText(Charsets.UTF_8).trim()
        assertEquals("Asset and pipeline stage3_rules_config.json must be identical", pipelineText, assetText)

        val parsed = Stage3RuleEngine.parseConfigJson(assetText)
        assertEquals("1.1.0", parsed.version)
        assertTrue(parsed.sweepDualPathGate.enabled)
        assertEquals(false, parsed.nonBatSweepToGlance.enabled)
        assertTrue(parsed.batVerticalGuardRule1.enabled)
        assertTrue(parsed.batAhrsGlanceRule2.enabled)
        assertEquals(0.35f, parsed.batAhrsGlanceRule2.minSub0GlancePath1, 1e-6f)
    }

    @Test
    fun `recoverHierarchicalProbs matches Python closed-form recovery to 1e-5`() {
        val root = loadParityResourceMap()
        val cases = root["prob_recovery_cases"] as List<Map<String, Any?>>
        for (c in cases) {
            val qArr = c["q_mid"] as List<Number>
            val qMid = FloatArray(qArr.size) { k -> qArr[k].toFloat() }
            val exp = c["expected"] as Map<String, Number>

            val actual = Stage3RuleEngine.recoverHierarchicalProbs(qMid)
            assertEquals(exp["p_no_shot"]!!.toFloat(), actual.pNoShot, 1e-5f)
            assertEquals(exp["p_is_shot"]!!.toFloat(), actual.pIsShot, 1e-5f)
            assertEquals(exp["p_fam_vert"]!!.toFloat(), actual.pFamVert, 1e-5f)
            assertEquals(exp["p_fam_cross"]!!.toFloat(), actual.pFamCross, 1e-5f)
            assertEquals(exp["p_fam_sweep"]!!.toFloat(), actual.pFamSweep, 1e-5f)
            assertEquals(exp["p_sub0_drive"]!!.toFloat(), actual.pSub0Drive, 1e-5f)
            assertEquals(exp["p_sub0_pd"]!!.toFloat(), actual.pSub0Pd, 1e-5f)
            assertEquals(exp["p_sub0_glance"]!!.toFloat(), actual.pSub0Glance, 1e-5f)
            assertEquals(exp["p_sub0_defl"]!!.toFloat(), actual.pSub0Defl, 1e-5f)
            assertEquals(exp["p_sub1_pull"]!!.toFloat(), actual.pSub1Pull, 1e-5f)
            assertEquals(exp["p_sub1_cut"]!!.toFloat(), actual.pSub1Cut, 1e-5f)
        }
    }

    @Test
    fun `applyAllRules matches Python apply_stage3_rules across all golden vectors`() {
        val root = loadParityResourceMap()
        val prodCfg = Stage3RuleEngine.parseConfigMap(root["prod_config"] as Map<String, Any?>)
        val allOnCfg = Stage3RuleEngine.parseConfigMap(root["all_on_config"] as Map<String, Any?>)

        val cases = root["rule_cases"] as List<Map<String, Any?>>
        for (rc in cases) {
            val name = rc["name"] as String
            val cfg = if ((rc["config_mode"] as String) == "prod") prodCfg else allOnCfg
            val rawPredCls = rc["raw_pred_cls"] as String
            val topProb = (rc["top_prob"] as Number).toFloat()
            val qArr = rc["q_mid"] as List<Number>
            val qMid = FloatArray(qArr.size) { k -> qArr[k].toFloat() }
            val hierProbs = Stage3RuleEngine.recoverHierarchicalProbs(qMid)
            val mountMode = rc["polar_mount_mode"] as String
            val fObj = rc["features"] as Map<String, Any?>

            fun flt(k: String, def: Float): Float = (fObj[k] as? Number)?.toFloat() ?: def
            fun fltNull(k: String): Float? = (fObj[k] as? Number)?.toFloat()
            fun bool(k: String, def: Boolean): Boolean = (fObj[k] as? Boolean) ?: def

            val features = Stage3RuleEngine.Stage3Features(
                deltaGz = flt("delta_gz", 0.0f),
                deltaPitch = flt("delta_pitch", 0.0f),
                omegaRoll = flt("omega_roll", 0.0f),
                impGz = flt("imp_gz", 6.0f),
                postImpactAccRatio = flt("post_impact_acc_ratio", 1.0f),
                hasPolar = bool("has_polar", false),
                watchPitchDeg = fltNull("watch_pitch_deg"),
                ahrsValid = bool("ahrs_valid", false),
                ahrsBladePitchDeg = fltNull("ahrs_blade_pitch_deg"),
                ahrsFaceRollDeg = fltNull("ahrs_face_roll_deg"),
                ahrsSwingYawDeg = fltNull("ahrs_swing_yaw_deg"),
                batGzMin = flt("bat_gz_min", 0.0f),
                bottomHandTimeLeadMs = flt("bottom_hand_time_lead_ms", 0.0f)
            )

            val res = Stage3RuleEngine.applyAllRules(
                rawPredCls = rawPredCls,
                topProb = topProb,
                hierProbs = hierProbs,
                features = features,
                polarMountMode = mountMode,
                config = cfg
            )

            val expectedPred = rc["expected_pred"] as String
            val expectedFired = (rc["expected_fired"] as List<*>).map { it as String }

            assertEquals("Case [$name] predictedShotType mismatch", expectedPred, res.predictedShotType)
            assertEquals("Case [$name] firedRules mismatch", expectedFired, res.firedRules)
        }
    }

    @Test
    fun `extractPreAhrsFeatures reads w_grav_z from channel 14 instead of channel 8`() {
        val numFrames = 300
        val anchorF = 220
        val sensorMatrix = Array(28) { FloatArray(numFrames) { 0f } }
        for (k in 0 until numFrames) {
            sensorMatrix[8][k] = 25.0f
            sensorMatrix[14][k] = 3.2f
        }
        val feats = Stage3RuleEngine.extractPreAhrsFeatures(sensorMatrix, anchorF, numFrames)
        assertTrue("impGz must read w_grav_z (channel 14 = 3.2), not w_acc_world_z (channel 8 = 25.0)", abs(feats.impGz - 3.2f) < 1e-4f)
    }
}
