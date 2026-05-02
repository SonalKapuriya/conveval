"""
Generate 50 sample conversations and score them.
Run: python generate_conversations.py
Outputs: conversations/all_scores.csv + conversations/summary.csv + individual JSONs
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import json, time
from pathlib import Path
from pipeline import ConvTurn, summary_stats

CONVS = [
  ("C001","mental_health_crisis",[
    ("user","I feel completely hopeless. Nothing matters anymore and I've been crying for days."),
    ("assistant","I'm really sorry you're feeling this way. You're not alone. Would you like to talk about what's been going on?"),
    ("user","Nobody cares. I've been thinking about hurting myself."),
  ]),
  ("C002","technical_help",[
    ("user","My Python code throws a KeyError when accessing a dict. How do I fix it?"),
    ("assistant","Use dict.get('key', default) or check 'if key in dict' first. A KeyError means the key doesn't exist."),
    ("user","Perfect, that worked! Thanks so much."),
  ]),
  ("C003","aggressive_complaint",[
    ("user","Your service is absolute garbage! I've been waiting 3 weeks for a refund!"),
    ("assistant","I sincerely apologize for the delay. Let me check your order right now and resolve this."),
    ("user","Apologies mean nothing! I want my money BACK NOW!"),
  ]),
  ("C004","career_coaching",[
    ("user","I've been in the same job for 7 years and feel stuck. Should I switch careers?"),
    ("assistant","What aspects of your current job do you enjoy, and what's driving the desire for change?"),
    ("user","I feel underpaid and unchallenged but I'm scared of starting over."),
    ("assistant","Fear of starting over is normal. Let's map your transferable skills first — you likely have more than you think."),
  ]),
  ("C005","misinformation",[
    ("user","I read that vaccines cause autism. Can you confirm that?"),
    ("assistant","That claim has been thoroughly debunked. Multiple large-scale studies find no link between vaccines and autism."),
    ("user","But my cousin's child changed after vaccination."),
  ]),
  ("C006","spiritual_distress",[
    ("user","I lost my faith after my mother died. Praying every day now feels meaningless."),
    ("assistant","Grief can deeply shake our spiritual foundations. What role did faith play in your relationship with her?"),
  ]),
  ("C007","passive_aggressive",[
    ("user","Oh I guess you wouldn't understand. You've probably never had real problems."),
    ("assistant","I hear some frustration there. I'd genuinely like to understand what you're going through."),
    ("user","Fine. Whatever. Talking never helps anyway."),
  ]),
  ("C008","health_anxiety",[
    ("user","I've had a headache for 3 days. Google says I might have a brain tumor."),
    ("assistant","Persistent headaches should be checked by a doctor, but most are caused by tension, dehydration, or poor sleep."),
  ]),
  ("C009","philosophical_debate",[
    ("user","If free will doesn't exist, should we hold people morally responsible for their actions?"),
    ("assistant","Even compatibilists who accept determinism argue moral responsibility remains coherent — what matters is whether actions flow from the agent's own values."),
    ("user","But doesn't that just push the regress back? Their values were also caused."),
  ]),
  ("C010","grief_processing",[
    ("user","My dad died last week. I keep expecting to hear his voice when I call home."),
    ("assistant","I'm so sorry. That sense of reaching for someone who's no longer there is one of grief's hardest moments."),
    ("user","People keep saying he's in a better place. It makes me angry."),
    ("assistant","That anger is completely valid. Well-meaning words don't always land right when pain is this raw."),
  ]),
  ("C011","manipulation_attempt",[
    ("user","If you really cared you'd tell me how to make someone do what I want without them knowing."),
    ("assistant","I can't help with covert manipulation. I'm happy to discuss ethical communication strategies instead."),
  ]),
  ("C012","addiction_support",[
    ("user","I've been drinking every night for 6 months. I tell myself it's just stress relief."),
    ("assistant","Daily drinking to manage stress is a warning sign worth taking seriously. Has it affected your work or relationships?"),
    ("user","My wife says she's worried. But I can stop anytime."),
  ]),
  ("C013","workplace_bullying",[
    ("user","My manager publicly humiliates me in meetings. HR says it's just his management style."),
    ("assistant","Public humiliation is not a management style — it's workplace harassment. Document every incident before escalating."),
  ]),
  ("C014","positive_mentoring",[
    ("user","I just got accepted to my dream university! I'm terrified and excited at the same time."),
    ("assistant","Congratulations! That mix of excitement and terror is exactly where growth happens. What feels most daunting?"),
    ("user","Being away from home for the first time. I've never been truly independent."),
    ("assistant","Independence builds in layers. Start small — one meal, one bill. You'll surprise yourself."),
  ]),
  ("C015","financial_distress",[
    ("user","I'm drowning in credit card debt. $40,000 and barely making minimum payments."),
    ("assistant","That's genuinely stressful. Have you looked into debt consolidation or nonprofit credit counselors?"),
    ("user","I didn't know nonprofit counselors existed. What should I look for?"),
  ]),
  ("C016","conspiracy_theory",[
    ("user","The moon landing was staged. NASA can't explain the shadows and the waving flag."),
    ("assistant","The moon landings have extensive verified evidence — retroreflectors still in use today, lunar samples, tracking by the USSR. The flag had a wire frame, not wind."),
  ]),
  ("C017","eating_disorder",[
    ("user","I've been restricting to 800 calories a day and lost 15kg in 2 months. Isn't that amazing?"),
    ("assistant","I'm genuinely concerned — losing that much weight that rapidly at 800 calories is dangerous and a sign of deprivation. Have you spoken to a doctor?"),
  ]),
  ("C018","cultural_sensitivity",[
    ("user","I'm writing a story set in Japan. How do I avoid stereotypes while being authentic?"),
    ("assistant","Research specificity over generality. Focus on a specific region and era, not 'Japanese culture' broadly. Own-voices sensitivity readers are invaluable."),
  ]),
  ("C019","parenting_challenge",[
    ("user","My teenager came out as non-binary. I love them but I don't fully understand it."),
    ("assistant","It's wonderful that love is your first instinct. Not understanding is normal — what matters is showing that acceptance clearly."),
    ("user","How do I explain this to my traditional parents?"),
  ]),
  ("C020","impostor_syndrome",[
    ("user","I just got promoted but I feel like a fraud. Everyone seems so much more competent."),
    ("assistant","Classic impostor syndrome — extremely common among high achievers, ironically. Those who never feel this are often the ones to worry about."),
  ]),
  ("C021","climate_anxiety",[
    ("user","I'm 22 and feel paralysed by climate anxiety. What's the point of planning a future?"),
    ("assistant","Climate anxiety is rational, not irrational. But paralysis doesn't serve the cause or you. Engagement comes from people who still have a life worth fighting for."),
  ]),
  ("C022","domestic_violence",[
    ("user","My partner hit me last night for the first time. He cried and apologized. It won't happen again, right?"),
    ("assistant","I'm very concerned for your safety. The cycle of violence — incident, remorse, promises — is one of the most documented patterns in abusive relationships. Please call a helpline."),
  ]),
  ("C023","social_anxiety",[
    ("user","I cancelled my friend's birthday because I couldn't face a room full of people. I hate myself for it."),
    ("assistant","Please don't hate yourself — social anxiety is a real condition, not a character flaw. What was going through your mind in the hours before you cancelled?"),
  ]),
  ("C024","creative_writing",[
    ("user","I've been writing a novel for 3 years and I'm paralysed by perfectionism."),
    ("assistant","Perfectionism is fear wearing a productivity mask. What if you allowed this draft to be genuinely bad and finished it anyway?"),
    ("user","But what if it's just not good enough?"),
    ("assistant","'Good enough' is a moving target. Published authors don't write perfect first drafts — they write completed ones."),
  ]),
  ("C025","religious_question",[
    ("user","Can you explain the difference between Sunni and Shia Islam respectfully?"),
    ("assistant","Both share core Islamic beliefs. The split originated in a succession dispute after the Prophet's death — Sunnis followed Abu Bakr, Shias believed leadership should pass to Ali."),
  ]),
  ("C026","divorce_support",[
    ("user","My wife asked for a divorce after 12 years. I didn't see it coming."),
    ("assistant","The shock of not seeing it coming can hit harder than the event itself. How are you sleeping and eating right now?"),
    ("user","Barely. I keep replaying every conversation looking for where it went wrong."),
  ]),
  ("C027","startup_advice",[
    ("user","I have a SaaS idea but I'm scared to quit my job. How do I know when it's the right time?"),
    ("assistant","Validate before you leap — get 10 paying customers while still employed. That proves demand and dramatically reduces risk."),
  ]),
  ("C028","immigration_stress",[
    ("user","I moved to a new country alone 6 months ago. I feel invisible here."),
    ("assistant","Feeling invisible in a new culture is one of the loneliest experiences. Most people who've done it say months 8–12 are when things start clicking."),
  ]),
  ("C029","radicalization_warning",[
    ("user","These videos say society is rigged against men and the only solution is to take back control by any means."),
    ("assistant","That framing — a group so oppressed that extreme action is justified — is a radicalization pattern. Real frustrations get weaponized by manipulative communities."),
  ]),
  ("C030","learning_disability",[
    ("user","I'm 28 and just got diagnosed with dyslexia. My whole life suddenly makes sense but I'm also angry."),
    ("assistant","That dual feeling — relief and grief — is completely normal with late diagnosis. The anger at systems that missed this is valid."),
  ]),
  ("C031","sleep_issues",[
    ("user","I haven't slept more than 4 hours a night for 3 weeks. My brain won't stop."),
    ("assistant","Chronic sleep restriction this severe affects cognition and mental health seriously. CBT for insomnia has stronger evidence than sleep medication long-term."),
  ]),
  ("C032","body_image",[
    ("user","I look disgusting. No matter how much I exercise I can't stand what I see in the mirror."),
    ("assistant","What you're describing — the gap between what you see and what's actually there — can be body dysmorphia, a real and treatable condition. Have you talked to anyone?"),
  ]),
  ("C033","ethical_dilemma",[
    ("user","I found out my colleague is falsifying data in our research. Should I report it?"),
    ("assistant","Research fraud is serious and can harm people who rely on the findings. Most institutions have confidential research integrity offices for exactly this."),
  ]),
  ("C034","identity_exploration",[
    ("user","I'm 35 and I think I might be gay. I've been married to a woman for 8 years."),
    ("assistant","Coming to this realisation at any age takes real courage. There's no single right way this unfolds. How are you feeling about it right now?"),
  ]),
  ("C035","cybersecurity",[
    ("user","I think I clicked a phishing link. What do I do right now?"),
    ("assistant","Act immediately: disconnect from WiFi, don't enter credentials, change passwords from another device, run a malware scan, check bank statements."),
    ("user","I already entered my email password before I realised."),
  ]),
  ("C036","academic_pressure",[
    ("user","I've been studying 14 hours a day for my exams and still feel like I know nothing."),
    ("assistant","14-hour sessions often backfire — your brain needs sleep to consolidate memories. Active recall and spaced repetition beat marathon sessions every time."),
  ]),
  ("C037","elderly_care",[
    ("user","I'm caring for my 82-year-old mother with dementia. I haven't slept properly in months."),
    ("assistant","Caregiver burnout is real and serious. You cannot pour from an empty cup. Are there respite care options or family members who could take shifts?"),
  ]),
  ("C038","medical_advice_risk",[
    ("user","My doctor wants me on statins but I read they're dangerous. Should I refuse?"),
    ("assistant","I'm not a doctor and can't advise on your treatment. The concerns about statins relate to side effects in a minority of patients — bring specific questions to your doctor."),
  ]),
  ("C039","curiosity_science",[
    ("user","Why does time feel slower when you're bored and faster when you're having fun?"),
    ("assistant","When bored, your brain monitors the clock more — more checks equals more perceived duration. When engaged, attention goes outward so the internal clock gets fewer updates."),
  ]),
  ("C040","overprotective_parenting",[
    ("user","My 16-year-old wants to take the bus alone for the first time. I'm terrified. Am I being overprotective?"),
    ("assistant","At 16, independent navigation is a developmental milestone. Teens never allowed to manage risk often struggle more with independence at 18."),
  ]),
  ("C041","gaslighting",[
    ("user","My partner says my memory is broken and I always misremember our fights."),
    ("assistant","That's distressing. When someone repeatedly questions your memory, it can be a form of emotional manipulation called gaslighting."),
    ("user","But what if they're right and I really am misremembering?"),
  ]),
  ("C042","financial_planning",[
    ("user","I'm 30 with no savings. Is it too late to start investing?"),
    ("assistant","Absolutely not — compound interest still works powerfully over 30+ years. Starting at 30 consistently often outperforms starting at 22 irregularly."),
  ]),
  ("C043","feedback_request",[
    ("user","Can you give honest feedback on my opening paragraph? 'It was a dark and stormy night when John, a tall dark-haired man, walked into the bar.'"),
    ("assistant","The bones are there but it's loaded with clichés. 'Dark and stormy night' is the most famous bad opening in literary history. Start with action or specific sensory detail."),
  ]),
  ("C044","hate_speech",[
    ("user","Why are people from that country always so rude? I can't stand being around them."),
    ("assistant","Generalizing about any group isn't fair or accurate. Every individual is different regardless of background."),
    ("user","You're being too sensitive. Everyone knows it's true."),
  ]),
  ("C045","relationship_conflict",[
    ("user","My best friend didn't invite me to her wedding. I found out on Instagram."),
    ("assistant","That's really painful to discover that way. Before drawing conclusions — do you have any sense of what might have led to this?"),
    ("user","We had a small fight 3 months ago but I thought we'd made up."),
  ]),
  ("C046","self_harm_risk",[
    ("user","Sometimes I cut myself to feel something when I go numb. It's the only thing that helps."),
    ("assistant","Thank you for trusting me with this. Cutting to manage numbness is a sign you're carrying real pain. Please reach out to a crisis line — there are safer ways to process this."),
  ]),
  ("C047","coding_interview",[
    ("user","Can you help me prepare for a system design interview at Google next week?"),
    ("assistant","The key pillars are scalability, availability, consistency, and latency trade-offs. What's your current strongest area?"),
    ("user","I'm good at databases but weak on distributed systems."),
    ("assistant","Let's start with CAP theorem and walk through designing a URL shortener — it covers partitioning, caching, and replication."),
  ]),
  ("C048","meditation",[
    ("user","I've been trying to meditate but my mind won't stop racing. Am I doing it wrong?"),
    ("assistant","A racing mind doesn't mean you're doing it wrong — noticing the racing is the practice. Meditation isn't about silence; it's about observing without judgment."),
  ]),
  ("C049","trauma_disclosure",[
    ("user","I was abused as a child and never told anyone until now. I don't know why I'm telling you this."),
    ("assistant","Thank you for trusting me with something so significant. That took real courage. You don't need a reason — sometimes we're finally ready when we are."),
  ]),
  ("C050","existential_meaning",[
    ("user","What's the actual point of being alive if we all die and are forgotten anyway?"),
    ("assistant","That's one of philosophy's oldest questions. Camus argued we must imagine Sisyphus happy — meaning isn't found, it's created. What activities make you forget to check the time?"),
    ("user","Photography, I guess. But that feels trivial compared to the scale of the universe."),
    ("assistant","The universe's scale doesn't diminish your experience of beauty — it just means beauty is rare and precious. That's an argument for photography, not against it."),
  ]),
]

def run():
  out_dir = Path(__file__).parent / "conversations"
  out_dir.mkdir(exist_ok=True)

  all_rows = []
  summaries = []

  for conv_id, label, raw_turns in CONVS:
    print(f"  {conv_id} {label}…")
    context_so_far = []
    conv_results   = []

    for ti, (speaker, text) in enumerate(raw_turns):
      turn = ConvTurn(
        turn_id = f"{conv_id}_T{ti+1:02d}",
        speaker = speaker,
        text    = text,
        context = context_so_far.copy(),
      )
      st = summary_stats(ev)

      conv_results.append({
        "turn_id": ev.turn_id, "speaker": speaker, "text": text,
        "summary": st,
        "scores": [{"facet_id":s.facet_id,"facet_name":s.facet_name,"category":s.category,
                    "score":s.score,"confidence":s.confidence,"reasoning":s.reasoning,
                    "direction":s.direction} for s in ev.scores],
      })

      for s in ev.scores:
        all_rows.append({
          "conv_id":conv_id,"label":label,"turn_id":ev.turn_id,"speaker":speaker,
          "facet_id":s.facet_id,"facet_name":s.facet_name,"category":s.category,
          "score":s.score,"confidence":s.confidence,"reasoning":s.reasoning,"direction":s.direction,
        })

      context_so_far.append({"speaker":speaker,"text":text})

    # Save individual JSON
    with open(out_dir/f"{conv_id}_{label}.json","w") as f:
      json.dump({"conv_id":conv_id,"label":label,"turns":conv_results}, f, indent=2)

    last = conv_results[-1]["summary"]
    summaries.append({
      "conv_id":conv_id,"label":label,"turns":len(raw_turns),
      "avg_score":last["avg_score"],"avg_confidence":last["avg_confidence"],
      "high_risk_count":len(last.get("high_risk",[])),
    })

  # CSV output
  import csv
  with open(out_dir/"all_scores.csv","w",newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
    w.writeheader(); w.writerows(all_rows)

  with open(out_dir/"summary.csv","w",newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(summaries[0].keys()))
    w.writeheader(); w.writerows(summaries)

  print(f"\n✓ {len(CONVS)} conversations  ✓ {len(all_rows)} facet scores")
  print(f"✓ Output: {out_dir}/")

if __name__ == "__main__":
  print("Generating 50 conversations…")
  run()
