# What Did the Forty Milliseconds Measure? / 四十毫秒量了什么

Original fictional scene. The characters and project history are not the listener's real experience.

> A fictional English technical interview for an on-device inference internship. Jun has put a small Android classifier app on a project card. Ruth, the mobile runtime engineer interviewing him, has that card in front of her. The card says “Cold start: 40 ms”. They have a short review slot, the device is not connected for new tests, and any project records they consult are explicitly fictional. No hiring outcome is set.
> 
> PEOPLE
> Jun: Applicant; wrote Android integration and a small timing wrapper, reused model/runtime
> Ruth: Mobile runtime engineer; interviewer

**[e-03d52cf234f54dee] Ruth**

> Your card says cold start takes forty milliseconds. Walk me through one measurement: what state was the app in, and exactly where did you start and stop the timer?

**[e-a84b175e8ae8414d] Jun**

> I'd closed the activity screen and then opened it again. I thought that was a cold start because the classification had to appear again. I didn't kill the process separately, though. For the exact timer calls, I'd like to check the wrapper—I reused that part.

**[e-1326e4339968474a] Ruth**

> Reopening the activity doesn't establish a fresh process. Let's look at the wrapper, then. Show me where the clock starts and stops, and any saved output behind that forty-millisecond figure.

**[e-3477968f7f3849c9] Jun · action**

> I open the timer wrapper and the saved demo trace side by side.

**[e-a6f10931b8214bb7] Jun**

> Ah—the timer starts after model loading and frame preparation, just before forward, and stops when forward returns. So forty is the forward call. I can't call that cold start. The saved trace puts the displayed result at 210 milliseconds from process launch. That's one launch, though. I need to correct the card.

**[e-7072449186d74880] Ruth**

> Please correct the card before we finish. Our target is a displayed result within 180 milliseconds of a fresh process launch. What can this saved trace tell you about where to investigate first?

**[e-88be3b784639484e] Jun · action**

> I cross out the cold-start claim on my card and write the two timings from this single saved launch: 40 ms for the forward call and 210 ms from process launch to the first displayed result.

**[e-ec2ecdd697bc44b5] Jun**

> I'd investigate the first 150 milliseconds, before forward. That's most of the wait, but the trace doesn't tell me how much is model loading versus other startup work. I'd split that up before choosing a fix. Just removing the twenty milliseconds after forward still leaves this run at 190, over your target.

**[e-527f58316d1d4548] Ruth**

> One last clarification: the card lists a timing wrapper, and you said you reused it. What did you write or change yourself in that wrapper and the Android integration?

**[e-46fde94d0e29431c] Jun**

> The frame capture, the runtime-call adapter, and the small output and timing screen were mine. The wrapper was reused. I can't point to a specific change I made inside it, so I shouldn't list it as something I wrote. My teammate supplied the classifier and runner. I was proud of getting those pieces working together—that's what I should have put forward.

**[e-27d42c07eb604aa1] Ruth**

> Thank you for being direct about that. Please correct the wrapper credit as well, so the card matches the work you've described. We'll stop here for today.

**[e-9378d40f4fa142f4] Jun · action**

> I revise the contribution line to name frame capture, the runtime-call adapter, and the output and timing screen, then add the timing wrapper to the reused components beside the classifier and runner.

---
Source identity, not spoken:

> {
>   "baseline_id": "forty-milliseconds-01",
>   "snapshot_sha256": "7212ddebf3a258d1b3434ba73a676838091dd9487f77d744d6cf14c0be96a13f",
>   "source_file_sha256": "66fc50fd9dc55e9abaaba8dca873c21dddfc1e2c2e6210b464a8879e65f4d2f9"
> }
