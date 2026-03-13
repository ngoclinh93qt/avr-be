"""
Seed script: Create admin account and populate fake data.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from app.core.supabase_client import supabase_service


async def create_admin():
    """Create admin@avr.com account using admin API (bypasses email confirmation)."""
    print("Creating admin account...")

    try:
        # Use admin API to create a pre-confirmed user
        response = supabase_service.admin.auth.admin.create_user({
            "email": "admin@avr.com",
            "password": "123456",
            "email_confirm": True,
        })
        user = response.user
        if user:
            print(f"  OK: Created user {user.email} (id: {user.id})")
            return user.id
        else:
            print("  FAIL: No user returned")
            return None
    except Exception as e:
        error_msg = str(e)
        if "already been registered" in error_msg.lower() or "already exists" in error_msg.lower():
            print("  User already exists, signing in...")
            try:
                result = await supabase_service.sign_in("admin@avr.com", "123456")
                user = result.get("user")
                if user:
                    print(f"  OK: Signed in as {user.email} (id: {user.id})")
                    return user.id
            except Exception as e2:
                print(f"  FAIL: Sign in failed: {e2}")
                return None
        else:
            print(f"  FAIL: {e}")
            return None


async def seed_fake_data(user_id: str):
    """Insert fake conversations, messages, pipeline runs, steps, and papers."""
    print("\nSeeding fake data...")

    now = datetime.now(timezone.utc)

    # ════════════════════════════════════════════════════════
    # Conversation 1: Completed topic analysis
    # ════════════════════════════════════════════════════════
    print("\n  [Conversation 1] Metformin & Diabetic Retinopathy")

    conv1 = await supabase_service.create_conversation(
        user_id=user_id,
        agent_type="topic_analyzer",
        title="Metformin and diabetic retinopathy prevention",
    )
    conv1_id = conv1["id"]
    print(f"    Created conversation: {conv1_id[:8]}...")

    # Pipeline run
    run1 = await supabase_service.create_pipeline_run(
        conversation_id=conv1_id,
        input_abstract="This study investigates the protective effects of metformin on diabetic retinopathy progression in type 2 diabetes patients. Using a retrospective cohort design with 500 patients from a tertiary hospital, we compare retinopathy progression rates between metformin users and non-users over a 5-year follow-up period.",
        language="en",
    )
    run1_id = run1["id"]
    print(f"    Created pipeline run: {run1_id[:8]}...")

    # Pipeline steps
    steps = [
        {"step_name": "assessment", "step_order": 1},
        {"step_name": "clarification", "step_order": 2},
        {"step_name": "enrichment", "step_order": 3},
        {"step_name": "research", "step_order": 4},
        {"step_name": "novelty", "step_order": 5},
        {"step_name": "gaps", "step_order": 6},
        {"step_name": "swot", "step_order": 7},
        {"step_name": "publishability", "step_order": 8},
        {"step_name": "suggestions", "step_order": 9},
    ]
    await supabase_service.create_pipeline_steps(run1_id, steps)
    print("    Created 9 pipeline steps")

    # Update steps to completed
    step_results = {
        "assessment": {
            "status": "completed",
            "started_at": (now - timedelta(minutes=5)).isoformat(),
            "completed_at": (now - timedelta(minutes=4, seconds=50)).isoformat(),
            "result": {"completeness_score": 78, "missing_critical": []},
        },
        "clarification": {
            "status": "skipped",
        },
        "enrichment": {
            "status": "skipped",
        },
        "research": {
            "status": "completed",
            "started_at": (now - timedelta(minutes=4, seconds=50)).isoformat(),
            "completed_at": (now - timedelta(minutes=3)).isoformat(),
            "result": {"total_found": 245, "total_ranked": 15, "avg_similarity": 0.74, "keywords": ["metformin", "diabetic retinopathy", "type 2 diabetes", "neuroprotection"]},
        },
        "novelty": {
            "status": "completed",
            "started_at": (now - timedelta(minutes=3)).isoformat(),
            "completed_at": (now - timedelta(minutes=2, seconds=40)).isoformat(),
            "result": {"score": 62, "reasoning": "Several studies have explored metformin's retinal effects, but the 5-year retrospective cohort design with 500 patients adds value.", "most_similar_paper": "Chen et al. 2023 - Metformin and DR progression", "differentiation": "Larger sample size and longer follow-up than existing studies"},
        },
        "gaps": {
            "status": "completed",
            "started_at": (now - timedelta(minutes=2, seconds=40)).isoformat(),
            "completed_at": (now - timedelta(minutes=2, seconds=20)).isoformat(),
            "result": {"gaps": [{"type": "methodological", "description": "Lack of randomized controlled trials for metformin's retinal effects", "how_filled": "Provides real-world evidence from large cohort", "strength": "moderate"}, {"type": "knowledge", "description": "Optimal dosing for retinal protection unclear", "how_filled": "Dose-response analysis possible with cohort data", "strength": "partial"}]},
        },
        "swot": {
            "status": "completed",
            "started_at": (now - timedelta(minutes=2, seconds=20)).isoformat(),
            "completed_at": (now - timedelta(minutes=2)).isoformat(),
            "result": {"strengths": [{"point": "Large cohort (n=500)", "reviewer_appeal": "High statistical power"}], "weaknesses": [{"point": "Retrospective design", "mitigation": "Use propensity score matching"}], "opportunities": [{"point": "Growing interest in drug repurposing", "action": "Position as repurposing evidence"}], "threats": [{"point": "Confounding by indication", "risk_level": "moderate"}]},
        },
        "publishability": {
            "status": "completed",
            "started_at": (now - timedelta(minutes=2)).isoformat(),
            "completed_at": (now - timedelta(minutes=1, seconds=40)).isoformat(),
            "result": {"level": "MEDIUM", "target_tier": "Q2", "confidence": 0.68, "reasoning": "Solid methodology but incremental contribution. Well-suited for specialty ophthalmology or diabetes journals.", "success_factors": ["Large sample", "Clinical relevance"], "risk_factors": ["Retrospective design", "Limited novelty"]},
        },
        "suggestions": {
            "status": "completed",
            "started_at": (now - timedelta(minutes=1, seconds=40)).isoformat(),
            "completed_at": (now - timedelta(minutes=1, seconds=20)).isoformat(),
            "result": {"suggestions": [{"action": "Add propensity score matching", "impact": "high", "effort": "medium", "priority": 1}, {"action": "Include biomarker analysis (VEGF, HbA1c trends)", "impact": "high", "effort": "medium", "priority": 2}], "quick_wins": ["Add subgroup analysis by diabetes duration", "Include OCT imaging data if available"], "long_term": ["Plan prospective validation study", "Collaborate with ophthalmology department"]},
        },
    }

    for step_name, updates in step_results.items():
        await supabase_service.update_pipeline_step(run1_id, step_name, updates)
    print("    Updated all step results")

    # Update pipeline run as completed
    final_result = {
        "status": "complete",
        "research": {
            "total_found": 245,
            "total_ranked": 15,
            "avg_similarity": 0.74,
            "keywords": ["metformin", "diabetic retinopathy", "type 2 diabetes"],
        },
        "novelty": {"score": 62, "reasoning": "Incremental but valuable contribution"},
        "publishability": {"level": "MEDIUM", "target_tier": "Q2", "confidence": 0.68},
        "metadata": {
            "processing_time_seconds": 220.5,
            "similar_papers_count": 15,
            "completeness_score": 78,
            "clarification_applied": False,
        },
    }
    await supabase_service.update_pipeline_run(run1_id, {
        "status": "completed",
        "started_at": (now - timedelta(minutes=5)).isoformat(),
        "completed_at": (now - timedelta(minutes=1, seconds=20)).isoformat(),
        "final_result": final_result,
        "keywords": ["metformin", "diabetic retinopathy", "type 2 diabetes", "neuroprotection"],
        "total_papers_found": 245,
        "total_papers_ranked": 15,
        "avg_similarity": 0.74,
        "processing_time_seconds": 220.5,
    })
    print("    Updated pipeline run: completed")

    # Messages
    await supabase_service.insert_message(conv1_id, "user", "user_message", {"text": "This study investigates the protective effects of metformin on diabetic retinopathy progression in type 2 diabetes patients. Using a retrospective cohort design with 500 patients from a tertiary hospital, we compare retinopathy progression rates between metformin users and non-users over a 5-year follow-up period.", "language": "en"}, run1_id)
    await supabase_service.insert_message(conv1_id, "system", "session_started", {"session_id": "fake-session-1", "history_enabled": True}, run1_id)
    await supabase_service.insert_message(conv1_id, "assistant", "analysis_progress", {"step": "research", "message": "Found 245 papers, ranked top 15", "progress": 55}, run1_id)
    await supabase_service.insert_message(conv1_id, "assistant", "analysis_progress", {"step": "novelty", "message": "Novelty score: 62/100", "progress": 65}, run1_id)
    await supabase_service.insert_message(conv1_id, "assistant", "analysis_complete", {"result": final_result, "processing_time_seconds": 220.5}, run1_id)
    print("    Inserted 5 messages")

    # Papers
    papers = [
        {"pmid": "38123456", "title": "Metformin reduces diabetic retinopathy progression: a systematic review", "authors": ["Chen L", "Wang H", "Zhang Y"], "year": 2024, "journal": "Diabetes Care", "doi": "10.2337/dc24-0123", "similarity": 0.89, "source": "pubmed", "abstract": "Systematic review of 12 studies examining metformin's effects on DR..."},
        {"pmid": "38234567", "title": "Anti-diabetic drugs and retinal vascular disease: population-based study", "authors": ["Smith J", "Doe A", "Park S"], "year": 2023, "journal": "JAMA Ophthalmology", "doi": "10.1001/jamaophthalmol.2023.5678", "similarity": 0.84, "source": "pubmed", "abstract": "We examined the association between anti-diabetic medications and retinal vascular outcomes..."},
        {"pmid": "37345678", "title": "Neuroprotective effects of metformin in diabetic eye disease", "authors": ["Kim HJ", "Lee YS"], "year": 2023, "journal": "Investigative Ophthalmology", "doi": "10.1167/iovs.23-34567", "similarity": 0.81, "source": "pubmed", "abstract": "Metformin exhibits neuroprotective properties through AMPK activation in retinal neurons..."},
        {"title": "Long-term outcomes of metformin therapy on microvascular complications", "authors": ["Nguyen TH", "Tran DM", "Pham VQ"], "year": 2024, "journal": "Journal of Diabetes Research", "similarity": 0.78, "source": "scholar", "abstract": "This longitudinal study followed 1200 T2DM patients..."},
        {"pmid": "37456789", "title": "Retrospective cohort analysis of DR risk factors in Southeast Asia", "authors": ["Tanaka K", "Suzuki M"], "year": 2023, "journal": "Asia-Pacific Journal of Ophthalmology", "similarity": 0.75, "source": "pubmed", "abstract": "Risk factors for diabetic retinopathy were analyzed in 3000 patients across 5 countries..."},
    ]
    await supabase_service.save_research_papers(run1_id, papers)
    print(f"    Inserted {len(papers)} research papers")

    # Update conversation status
    await supabase_service.update_conversation(conv1_id, {"status": "completed"})

    # ════════════════════════════════════════════════════════
    # Conversation 2: With clarification (Vietnamese)
    # ════════════════════════════════════════════════════════
    print("\n  [Conversation 2] Curcumin & Liver Cancer (Vietnamese)")

    conv2 = await supabase_service.create_conversation(
        user_id=user_id,
        agent_type="topic_analyzer",
        title="Curcumin trong dieu tri ung thu gan",
    )
    conv2_id = conv2["id"]

    run2 = await supabase_service.create_pipeline_run(
        conversation_id=conv2_id,
        input_abstract="Nghien cuu tac dung cua curcumin len te bao ung thu gan.",
        language="vi",
    )
    run2_id = run2["id"]

    steps2 = [
        {"step_name": "assessment", "step_order": 1},
        {"step_name": "clarification", "step_order": 2},
        {"step_name": "enrichment", "step_order": 3},
        {"step_name": "research", "step_order": 4},
        {"step_name": "novelty", "step_order": 5},
        {"step_name": "gaps", "step_order": 6},
        {"step_name": "swot", "step_order": 7},
        {"step_name": "publishability", "step_order": 8},
        {"step_name": "suggestions", "step_order": 9},
    ]
    await supabase_service.create_pipeline_steps(run2_id, steps2)

    # Assessment: incomplete → clarification needed
    await supabase_service.update_pipeline_step(run2_id, "assessment", {
        "status": "completed",
        "started_at": (now - timedelta(hours=2)).isoformat(),
        "completed_at": (now - timedelta(hours=1, minutes=59)).isoformat(),
        "result": {"completeness_score": 35, "missing_critical": ["methodology", "population", "outcome"]},
    })
    await supabase_service.update_pipeline_step(run2_id, "clarification", {
        "status": "completed",
        "started_at": (now - timedelta(hours=1, minutes=59)).isoformat(),
        "completed_at": (now - timedelta(hours=1, minutes=58)).isoformat(),
        "result": {"questions_generated": 3},
    })
    await supabase_service.update_pipeline_step(run2_id, "enrichment", {
        "status": "completed",
        "started_at": (now - timedelta(hours=1, minutes=55)).isoformat(),
        "completed_at": (now - timedelta(hours=1, minutes=54)).isoformat(),
        "result": {"enriched": True},
    })

    # Mark remaining steps as running (in progress)
    await supabase_service.update_pipeline_step(run2_id, "research", {
        "status": "completed",
        "started_at": (now - timedelta(hours=1, minutes=54)).isoformat(),
        "completed_at": (now - timedelta(hours=1, minutes=52)).isoformat(),
        "result": {"total_found": 180, "total_ranked": 12, "avg_similarity": 0.68},
    })
    for s in ["novelty", "gaps", "swot", "publishability", "suggestions"]:
        await supabase_service.update_pipeline_step(run2_id, s, {"status": "completed", "result": {}})

    await supabase_service.update_pipeline_run(run2_id, {
        "status": "completed",
        "enriched_abstract": "This in-vitro study investigates the cytotoxic effects of curcumin on HepG2 hepatocellular carcinoma cell lines. Using MTT assay and flow cytometry, we evaluate dose-dependent apoptosis induction at concentrations of 10-100 uM over 48 hours.",
        "started_at": (now - timedelta(hours=2)).isoformat(),
        "completed_at": (now - timedelta(hours=1, minutes=50)).isoformat(),
        "keywords": ["curcumin", "hepatocellular carcinoma", "HepG2", "apoptosis"],
        "total_papers_found": 180,
        "total_papers_ranked": 12,
        "avg_similarity": 0.68,
        "processing_time_seconds": 600.0,
    })

    # Messages for conv2
    await supabase_service.insert_message(conv2_id, "user", "user_message", {"text": "Nghien cuu tac dung cua curcumin len te bao ung thu gan.", "language": "vi"}, run2_id)
    await supabase_service.insert_message(conv2_id, "assistant", "clarification_needed", {
        "intro_message": "Abstract cua ban can them thong tin. Vui long tra loi cac cau hoi sau:",
        "questions": [
            {"id": "methodology", "question": "Ban su dung phuong phap nghien cuu nao? (in vitro, in vivo, clinical trial?)", "element": "methodology", "priority": 1},
            {"id": "population", "question": "Dong te bao hoac doi tuong nghien cuu cu the?", "element": "population", "priority": 1},
            {"id": "outcome", "question": "Chi tieu danh gia chinh la gi?", "element": "outcome", "priority": 2},
        ],
        "skip_allowed": False,
    }, run2_id)
    await supabase_service.insert_message(conv2_id, "user", "user_answer", {"question_id": "methodology", "answer": "In vitro, su dung MTT assay va flow cytometry"}, run2_id)
    await supabase_service.insert_message(conv2_id, "user", "user_answer", {"question_id": "population", "answer": "Te bao HepG2 hepatocellular carcinoma"}, run2_id)
    await supabase_service.insert_message(conv2_id, "user", "user_answer", {"question_id": "outcome", "answer": "Ty le apoptosis va IC50 cua curcumin"}, run2_id)
    await supabase_service.insert_message(conv2_id, "assistant", "analysis_complete", {"result": {"status": "complete"}, "processing_time_seconds": 600.0}, run2_id)
    print(f"    Created conversation with clarification flow (6 messages)")

    # Papers for conv2
    papers2 = [
        {"pmid": "37890123", "title": "Curcumin induces apoptosis in hepatocellular carcinoma cells via mitochondrial pathway", "authors": ["Li X", "Zhang W"], "year": 2023, "journal": "Phytomedicine", "similarity": 0.85, "source": "pubmed"},
        {"pmid": "38012345", "title": "Natural compounds targeting liver cancer: a comprehensive review", "authors": ["Patel R", "Kumar A"], "year": 2024, "journal": "Cancer Letters", "similarity": 0.72, "source": "pubmed"},
        {"title": "Dose-dependent cytotoxicity of curcumin analogs in HepG2 cells", "authors": ["Tran MT", "Le HN"], "year": 2023, "journal": "Vietnamese Journal of Pharmacy", "similarity": 0.80, "source": "scholar"},
    ]
    await supabase_service.save_research_papers(run2_id, papers2)
    print(f"    Inserted {len(papers2)} research papers")

    await supabase_service.update_conversation(conv2_id, {"status": "completed"})

    # ════════════════════════════════════════════════════════
    # Conversation 3: Active/in-progress
    # ════════════════════════════════════════════════════════
    print("\n  [Conversation 3] Machine Learning & COVID-19 (active)")

    conv3 = await supabase_service.create_conversation(
        user_id=user_id,
        agent_type="topic_analyzer",
        title="ML-based COVID-19 severity prediction",
    )
    conv3_id = conv3["id"]

    run3 = await supabase_service.create_pipeline_run(
        conversation_id=conv3_id,
        input_abstract="We develop a machine learning model using XGBoost and random forest to predict COVID-19 severity from routine blood tests. Training on 2000 patient records from 3 hospitals, we evaluate prediction accuracy for ICU admission within 48 hours of presentation.",
        language="en",
    )
    run3_id = run3["id"]

    steps3 = [
        {"step_name": "assessment", "step_order": 1},
        {"step_name": "clarification", "step_order": 2},
        {"step_name": "enrichment", "step_order": 3},
        {"step_name": "research", "step_order": 4},
        {"step_name": "novelty", "step_order": 5},
        {"step_name": "gaps", "step_order": 6},
        {"step_name": "swot", "step_order": 7},
        {"step_name": "publishability", "step_order": 8},
        {"step_name": "suggestions", "step_order": 9},
    ]
    await supabase_service.create_pipeline_steps(run3_id, steps3)

    # Mark first 3 steps done, research running
    await supabase_service.update_pipeline_step(run3_id, "assessment", {"status": "completed", "result": {"completeness_score": 85}})
    await supabase_service.update_pipeline_step(run3_id, "clarification", {"status": "skipped"})
    await supabase_service.update_pipeline_step(run3_id, "enrichment", {"status": "skipped"})
    await supabase_service.update_pipeline_step(run3_id, "research", {"status": "running", "started_at": now.isoformat()})

    await supabase_service.update_pipeline_run(run3_id, {
        "status": "running",
        "started_at": now.isoformat(),
    })

    await supabase_service.insert_message(conv3_id, "user", "user_message", {"text": "We develop a machine learning model using XGBoost and random forest to predict COVID-19 severity from routine blood tests.", "language": "en"}, run3_id)
    await supabase_service.insert_message(conv3_id, "assistant", "agent_thinking", {"message": "Abstract is 85% complete. Proceeding with analysis...", "step": "ready", "progress": 45}, run3_id)
    await supabase_service.insert_message(conv3_id, "assistant", "analysis_progress", {"step": "research", "message": "Searching PubMed and Google Scholar...", "progress": 50}, run3_id)
    print("    Created active conversation (research in progress)")

    print("\n" + "=" * 50)
    print("Seed complete!")
    print(f"  User: admin@avr.com")
    print(f"  User ID: {user_id}")
    print(f"  Conversations: 3")
    print(f"  - Completed: Metformin & DR (5 papers)")
    print(f"  - Completed: Curcumin & Liver Cancer (3 papers, with clarification)")
    print(f"  - Active: ML & COVID-19 (in progress)")
    print("=" * 50)


async def main():
    print("=" * 50)
    print("AVR Seed Script")
    print("=" * 50)

    user_id = await create_admin()
    if not user_id:
        print("\nFailed to create/get admin user. Aborting.")
        return

    await seed_fake_data(user_id)


if __name__ == "__main__":
    asyncio.run(main())
