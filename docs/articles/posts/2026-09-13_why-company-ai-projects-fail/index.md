---
date:
  created: 2026-09-13
  updated: 2026-09-13
authors:
  - richard
slug: why-company-ai-projects-fail
categories:
  - Automation
tags:
  - AI
---

# Why 95% of company AI projects fail

It's an interesting time to be alive. The "AI transformation" is happening.

Many business owners feel FOMO on AI adoption. Yet, allegedly 95% of AI projects in companies fail, according to an MIT report. Why is this?

I've talked to business owners and AI automation agencies. This is what I found.

<!-- more -->


## Challenge: GenAI is non-deterministic

This is the big one. If you think like a software engineer, AI is finicky / fuzzy compared to cold hard code. LLM's use a literal random number generator to produce their outputs.

So if you use LLM's for automation, you will have unexpected things happening.

Most of the risk surfaces when you're using **AI Agents** to automate tasks. But there is a more boring and deterministic approach to automation: **AI workflows**.


## AI Agents vs. AI Workflows

These are the two main approaches to AI automation.

### AI Agents

> **Agents** [] are systems where LLMs dynamically direct their own processes and tool usage, maintaining control over how they accomplish tasks.

This is currently the most hyped up version of automation:

Trigger an LLM, and let it run wild with tools.

And by "let it run wild with tools" I mean:

Give it a sense of which tools it can use, and let the LLM decide which tools it wants to call, and how.

Tools can be: reading / writing files on your computer, using a calculator, doing web search. Anything you might be able to do with a computer that could be useful for the task at hand.

The flexible "blank canvas" approach here makes it quite interesting, but every little mistake adds up, and over time, results can get wild. This is not what you want in a company procedure.

So it currently requires a lot of babysitting to be productive with agents, which kind of defeats the purpose of automation.

### AI Workflows

Less flashy, more simple and deterministic.

> **Workflows** are systems where LLMs and tools are orchestrated through predefined code paths.

AI workflows are simple software procedures, with deterministic logic. The are "set in stone" and designed upfront with a lot of care. 

Being predefined makes them less flexible, but that's exactly what you want in a company with SOP's. Only where it makes sense, LLM calls are made.

This way, you keep the automation in check, and things don't spiral out of control by a hallucinating model.

Every LLM call has guardrails with enforced checks and fallbacks. So even if an LLM model completely shits the bed, your workflow can still move on in a reasonable way.


## Recipes for failure

The common patterns of AI projects that fail are:

- One system trying to automate everything

- Automating workflows that still need human feedback

- Architecting high level production systems

### One system trying to automate everything

The man who chases two rabbits, catches none. If you try to automate too much with a single system, the chances of failure increase geometrically. And that is why it so often fails.

The better approach is to take one procedure at a time, something that is done manually so you know exactly what needs to be done. You know the exceptions, you know the intricate details. Then it's a lot easier to start building an automation for this.

Don't "automate the marketing" for your company, but automate budgeting your google ads account for example.

### Automating workflows that still need human feedback

If you try to fully automate a workflow where you should be checking things before moving to the next step, you're gonna have a bad time.

For example, sending emails. If you think your agent can read incoming emails, figure out a reply, and send them off. This might work well for 90% of the cases. But unexpected situations can cause massive disasters.

Solution: Automate 95% of the process, but have a human give the final green light before moving on. So let the AI draft a reply, you're the one to send it off.

**Architecting high level production systems**

AI models wrapped up in coding harnesses are getting extremely good at software engineering. But when architecting high level production systems, AI currently just lacks some of the awareness, company history, that's required to lead this to a good outcome.

Solution: Human / agent collaboration. Have a senior engineer go back and forth with the coding agent to come to a good outcome.


## What works well

As we'll see, the non-deterministic nature of genAI explains why it so often fails to automate a business procedure.

The common theme is that typically the more boring automations, that don't look exciting or flashy, are working the best.

This agrees with Anthropic's take on the matter:

> we recommend finding the simplest solution possible, and only increasing complexity when needed.

After talking to business owners, these are some AI project areas that are either working well or failing miserably.

### Data analytics

Most companies are collecting data. And LLM's are fantastic at pulling data from a database, and drawing conclusion.

Especially if you give it the proper context of what they have access to, and all the relations between entities.

This can be a great way to answer business questions with subtle nuances that are different every time. For example, a question like: "What was last quarter's revenue from returning European customers?" and "How many of them spent over $1,000?".

This used to take a MySQL (or Tableau/Power BI) expert and a complicated query for every single question.

Now, most state of the art LLM's are smart enough to connect the dots, and pull the correct data out.

Pro tip: Give the LLM read-only access to your database. For analytics there's no need to change the database. We've all heard the horror stories of "the AI wiped out production".

### **Specialised translation**

LLM's are pretty good at language. So if you have a specific translation job to do, where context matters a lot, they can do a great job.

If context matters a lot, you do have to make sure to give that context to the LLM, obviously.

Examples of this could be: Translating restaurant menu's into different languages. Here, it's important to not translate everything literally, but now that everything is food related. And if a menu item says "Margarita" it's important to know whether it's under the pizza's or the cocktails section.

Another example could be: Translating subtitles for technical tutorial videos. Having the context of the technical topic, and jargon is important here. But once you give it this context, LLMs can be great.

This is a perfect example of where a workflow performs a lot better than agents.

### **Research**

LLMs are great at processing large amounts of text. If you need to do research on a certain topic, you can let LLMs search the internet for sources, and cross reference different findings.


## Conclusion

AI projects tend to fail because companies try to hastily adopt new workflows out of
fear of missing out, and by nature, LLMs are non-deterministic.

The approach that works reliably is: keeping it simple.

When building applications with LLMs, use the simplest solution possible, and only increase complexity when needed.

This might mean not building "agentic" systems at all, but just stick to workflows.
