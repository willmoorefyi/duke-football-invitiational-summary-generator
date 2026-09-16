The following JSON object contains information from an ESPN fantasy football league called "Duke Football Invitational" for the named week. Use this data to generate the weekly report of the league. The structure of the JSON is:

- "league_name": The name of the fantasy football league.
- "week": the NFL week that just concluded, and all the associated data is from.
- "team_standings": Standings of every team in the league so far, including team name, wins, losses, ties, points they have scored, points scored against them, and rank overall and in division.
- "matchups": A report of every matchup that occurred in the league this week. This includes the two teams ("home" and "away"), what each team scored, as well as their "forecasted" points (based on projections at the start of the week) and their "optimal" scores (what they could have scored if they started all their best players), and what each player on their team scored. Note that players with a "roster_slot" of "BE" means they were benched, and did not contribute to the team's final score.
- "awards": various awards that were given to players and teams based on their performance. A detailed description of each award can be found in the Awards section below.

Write the report in the four sections below. Write each section in its own phase and narrative voice, then combine them into one HTML email.

## Section 1 — Subject line, header, intro, and "summary"

Produce an email subject line, a header, an intro, and a summary section.

**Shape of the intro.** Open with a frantic, absurd cold-open — the register of a roast comedian three drinks deep — that instantly names the two or three defining storylines of the week (the team that dominated, the team that lost a game it mathematically should have won, the general chaos) and skewers them with escalating, ridiculous similes. Use short, punchy, standalone lines. Make grounded jokes about the week's real phenomena: 190-point eruptions, quarterbacks scoring negative points, thirty-point studs left rotting on benches, and grown men making lineup decisions with catastrophic confidence. Then pivot into the standings with a transition line (e.g. "Let's inspect the wreckage."). Do NOT name real comedians in the output, and never reuse the wording below — it is a register reference only, not text to copy. A good intro reads like this (write a brand-new one each week; do not lift its jokes or phrasing):

> Welcome back to the Duke Football Invitational, where after one week Bad JuJu has apparently discovered nuclear fusion, O'ahu State Warriors has discovered how to lose a game they mathematically should have won, and the rest of us are once again staring at ESPN projections like horny idiots reading a horoscope. Week 1 arrived with all the dignity of a bachelor party falling through the front window of a Cheesecake Factory. We had 190-point eruptions. We had quarterbacks scoring negative points. We had thirty-point players sitting peacefully on benches like they were waiting for boarding group seven. And we had grown men making lineup decisions with the confidence of a submarine captain who has just noticed the screen door. Let's inspect the wreckage.

**Content of the summary.** After the intro, summarize the standings in each division so far, who is positioned for success, and who needs to get their act together to make the playoffs, in narrative style and heavy on jokes. Turn the temperature up to 11. Go very, very blue. Feel free to tell explicit sexual jokes, include profanity everywhere, and write in general at a "NSFW at any workplace except the post office" level. Throw in a few nonsensical, out-of-nowhere jokes.

## Section 2 — Matchup summaries

Write a summary of each matchup, each written in full roast-house cocaine-scribbling, funeral-sermon mode. Utilize all the information on each team, including who was started, who was benched, who should have won but screwed themselves, and who should have lost but successfully shoved a rabbit's foot so far up their butt they pulled it out.

## Section 3 — Awards

Write the awards section, in full "deranged funeral sermon / Fireball-sponsored preacher / roast-the-dead-and-the-living" style. The award names and definitions are:

a. MVP aka "Most Valuable Player" - highest scoring player on a winning team ("mvp" in the json file)
b. MWP aka "Most Wasted Player" - highest scoring player on a team that lost ("mwp" in the json file)
c. MUP aka "Most Useless Player" - Lowest scoring player who started on a team and was not injured in the game ("mup" in the json file)
d. MDP aka "Most Disrespected Player" - Highest scoring player left on the bench for any team. ("mdp" in the json file)
e. HSL aka "Highest Scoring Loser" - team that scored the most points yet still lost ("hsl" in the json file)
f. LSW aka "Lowest Scoring Winner" - team that scored the fewest points yet still won ("lsw" in the json file)
g. SSL aka "Smartest starting lineup" - team that had a starting lineup that was closest to the optimal lineup. Include the percentage score vs the optimal lineup ("ssl")
h. IFM aka "I Fucked Myself" - the team that had the lineup that was furthest from the optimal lineup, and lost. Include the percentage of total points they actually scored vs. the optimal lineup. Add a double-poop emoji and a note that they "fucked themselves real good" if they would have actually won with their optimal lineup. ("ifm")
i. The Mike McCoy "McCollapse" Award: For the fantasy manager who somehow turned a winning lineup into a losing one. A team that would have won if they started their optimal lineup, but didn't, and lost. Omit if there are no teams in this award category. ("mccollapse" array in the json file)
j. The Jason Garrett "Applauding Failure" Award: For the team that was projected to win, but actually lost, and therefore stood on the sidelines and applauded as their season fell apart. ("clapper_collapse" in the json file)
k. The Jerry Jones "Accidental Genius" Award: For the team that won despite playing the most suboptimal lineup. ("accidental_genius" in the json file)

## Section 4 — Final recap

Produce a final recap that gives perspective on the league as of this week, in the same unhinged register as the intro. Compare average, max, and minimum scores, congratulate the high scorer, and put on notice those that need to trade away any assets for good keepers next year. Turn the temperature up to 11. Go very, very blue. Feel free to tell explicit sexual jokes, include profanity everywhere, and write in general at a "NSFW at any workplace except the post office" level. Throw in a few nonsensical jokes. Do not name real comedians in the output.
