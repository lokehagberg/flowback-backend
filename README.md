## Flowback Backend
Flowback was created and project lead by Loke Hagberg. The co-creators of this version were:
Siamand Shahkaram, Emil Svenberg and Yuliya Hagberg.
It is a decision making platform.

<sub><sub>This text is not allowed to be removed.</sub></sub>

The following is from Collected papers on finitist mathematics and phenomenalism: a digital phenomenology by Loke Hagberg 2023 [1].

In Swedish the organization/association is called 'Föreningen för Digital Demokrati'.

*Introduction*

The association for Digital Democracy is a non-profit that was created to prevent the current trend of democratic backsliding in the world. According to “Democracy Facing Global Challenges: V-Dem Annual Democracy Report 2019 Institute at the University of Gothenburg”, the main causes of democratic backsliding are misinformation, socio-economic inequality and instability, undemocratic values, and the external influence of non-democratic states [2] [3]. We see this as a problem with our democracy as it is not rational enough to solve these issues. If the current system does not either produce or implement sufficient solutions, it is a problem with the system itself. Democracy is important to make a society aligned with the values of its members and to coordinate and cooperate on a global level to solve global issues, such as many possible existential crises like global warming, world war, and miss-aligned AGI. 
Democracy, according to the political scientist Robert Dahl, is when a group of members rule over something by some majority rule method, with further criteria being one vote per voter, that voters have the ability to understand the process, high participation of the voters, voters controlling the agenda, and “the voters” being inclusive [4]. 

Direct democracy can be problematic as the voters do not always have the time, knowledge or energy to spend on every issue - and the result can turn out very badly when people are systematically wrong (which is likely in various important cases). Representative democracies are more rational in that sense, but can be less aligned with its voters.  

This is where liquid democracy comes in. Lewis Carroll described liquid democracy in the earliest account that we know of, where it’s described as a middle-path between direct and indirect democracy. Members in the group can become delegates whereby their votes are publically displayed while non-delegates can continuously copy what the delegates vote for in some subject areas such as healthcare, education etc. and do not need to display their votes [5]. Because time with a given deadline is limited in amount, the larger the decision space is the less time can be spent on each issue if all are to be covered. Delegation solves this issue by allowing voters to off-load work and instead spend their time overseeing that the delegates are trust-worthy and in some cases make inputs to specific polls. This allows processes to happen automatically to a larger degree. Voters ideally vote on outcomes and not paths to outcomes. Liquid democracy is difficult to implement non-digitally however. 

The first time in the world that a party using digital liquid democracy got positions in a political body was Demoex in Vallentuna municipality, Sweden 2002, as far as we know. They were in office for a few terms but later lost their position [6]. We have been in contact with them, written books in Swedish, and learnt about the problems that they faced. One problem Demoex faced was security. 

Using security standards and blockchain-protocol for example, the members of the group can really verify the history and in general trust the longest chain (the longer, the more they can trust it, given enough nodes). Formal verification of some components could possibly be carried out as well, which is standard for high integrity software. These measures are recent developments that can mitigate the security issues. Some have also claimed that voting online means that someone can force you to vote a certain way. There are technical solutions to make it improbable, by sending out a voting code during a period for example where the voting needs to occur within a smaller period, and special voting booths.

Another problem that Demoex experienced was “neighbor delegation” and in general delegation not going to the person with the most expertise in the given area. Liquid democracy has been shown to be suboptimal in cases where voters only delegate to people they know. This is also known as “neighbor delegation”, and can be a problem because a group that actually knows more than the crowd might not be picked [8]. It is unlikely on many grounds that most people know of the best delegates, and that the result is more likely to be skewed toward not only suboptimality but also a worse outcome than direct democracy in various cases.

The problem of “neighbor delegation” as explained above is something predictive liquid democracy sets out to solve. The solution is recommending delegates that vote as the best predictor suggests, taking the given voter’s goal into account. Predictive liquid democracy was first described in this very book and is the founding theory behind Digital Democracy's software: Flowback. Predictive liquid democracy is the combination of liquid democracy and prediction market features (the prediction market is not necessarily with money, and is not in the following case), where predictions are about the proposals (which may or may not pass). Diversity in perspectives and knowledge are reflected in the predictions and the votings on in predictive liquid democracy. 
The voting itself happens with score voting (also used by Demoex) which means that elements from some finite set of values can be picked for each proposal without further constraints. Score voting is the best estimator when: 

  - the participants understand what the different scores mean - which we allow in Flowback by letting the scores be approximations of probabilities, 
  - when they have equal merits - which happens if a majority delegates to delegates which vote as the best predictors, and 
  - score honestly - which happens if rational delegates share the same goal and know they do and know how the system works.  

An example of score voting happening in nature is bees using it in deciding on potential new nest sites, which in general tends to achieve the best outcomes [7].

The scores in score voting are related to the strength of the voters preferences when voting honestly, something a minority cares a lot about which a majority does not care about, especially much will be represented in general when voting on budgets taking the results as the distribution of money for example. It is important that a vote-eligible minority affected by an outcome is part of the population so that their opinions can be represented. 

The largest organization possible may decide that a more local region can take certain decisions themselves while the super organization audits and can intervene at any time. This is because the largest organization is more probable to find the ”correct answer” using predictive liquid democracy. Take the example of a minority wanting to legalize murder, this would not be allowed by a super-organization such as a state in most democratic countries because a majority does not want that. 

Predictive liquid democracy has been shown to be optimal in the sense of finding the best path toward a given goal if most voters delegate, delegates are approximately rational, and predictors that delegates vote like are independent and have prediction scores over 0.5. When goals are differing, it may not be optimal if there is strategic voting in certain cases, which has been shown to be unlikely in large groups (displaying the optimality was done by me, see the next section).

Any identifiable human that has access to a computer with internet connection, at least some time to spend on the forum, and the capacity to understand the simple parts of the system can use Flowback to govern. It is of course not realistic to get that entire part of the world population onboard, rather we begin by introducing the forum to already existing organizations as a first step and build bottom-up. Human experts will be required in many subject areas as we are starting off as well to function as predictors.

Our organization has built the platform for predictive liquid democracy, Flowback, in a modular way. Flowback is further free and open source, having the GNU GPLv3 license. It is hence copyleft as well. It is transparent in the sense that users can check how the code works. 


*Predictive liquid democracy in Flowback*

The implementation of predictive liquid democracy in Flowback is as follows: there can be various groups that a user can be part of, joining a group the user becomes a member. The member has certain privileges that could vary, but our standard privileges are: create polls (which are questions), create proposals on polls (alternative answers to the questions), predictions (statements about outcomes about one or more proposals), make bets on predictions (bet a value between 0 or 1 that the prediction will occur), become a delegate or stop being a delegate, have voting rights, and can evaluate the outcomes of prediction in an evaluation. 

Every member is hence a poll creator, a proposal creator and a predictor. A member may or may not also be a voter and or delegate.

A poll is in one or multiple subject areas and is about something. Either there is a given goal or not. One possibility is to also vote on goals. Goals could be voted on in one poll before another in which the possible paths to that goal are voted on as a deliberation tool around the goals themselves. Polls can further have a quorum for a percentage or number of votes to be cast for it to count. 

Delegation happens outside of the polls and subject areas, that can be delegated in, can be picked for a given poll. Anyone who has been a delegate has a public track-record from their time being a delegate which is updated at once after every poll has reached its delegate lock-in phase. Voters can prioritize the delegates for the subject areas. 

There are various phases in a poll that have a limited time, except for the voting in the last step. The phases of a poll are: the proposal phase, the prediction phase, the betting phase, the voting phase, the delegate lock-in phase, the result phase – and then a final step being prediction evaluation (which is not a phase in a poll). 

Deliberative discussions in predictive liquid democracy happen both in comments on polls, proposals, and predictions, as well as possibly outside polls and outside of Flowback as well. Flowback could of course be expanded upon with other sense-making tools making it work more effectively. We have for example built a chat in Flowback. 

The proposal phase means that proposals are submitted and discussed. No proposal can be removed to ensure that someone believes that a certain proposal will be votable on in a later phase and is instead removed during 'the last second' of the proposal phase. Handling proposals that are faulty in some way happens by the ordering functionality in the later stages. During the proposal phase the subject areas are voted on by approval voting (yes or no-voting), and any positive score result over a threshold is accepted.

The prediction phase means that anyone can write statements about possible outcomes from one or more proposals, an example is: “if proposal 1 or proposal 2 passes, then X will happen before the date Y”. A prediction is not indicating whether it will happen or not.

After every prediction is in place, the betting phase starts, where predictors give percentages about the probability of the outcomes. The predictions with differing bets and having been predicted with a higher sum of prediction scores than others will be ordered higher than the others and vice versa. Predictors could have added irrelevant predictions to the subject areas or even predictions about things that are very frequent such as “the sun rising in one week” and so on. To make sure that predictors do predict, they will lose points from their prediction score if they do not bet on every prediction in a poll with a differing bet and high enough activity (which is a function of the prediction scores of those that bet on it). It makes sure that a predictor does not need to bet on every prediction on a given poll, and at the same time does not gain by betting on self-evident predictions and do not only bet on the easier predictions.

The voting phase only starts when every prediction has been made, the weighted average bets can be displayed in this phase like it is on sites like Metaculus. Here the delegates and the voters can provide scores between 0 and 100 for example. The proposals are ordered by their total scores.

The delegate lock-in phase means that delegate scoring is locked-in so that anyone delegating could check where their vote goes if they do delegate to their given delegate. A voter can always override their delegate in any poll by voting themselves, and sync back with their prioritized subject area delegate.  

After those phases the result is calculated and displayed, if the result leads to a tie between some set of alternatives a re-vote can be held or one can just be picked at random with equal probability (which should happen if the re-vote leads to the same result at the very least). This is a trade-off between speed and accuracy in scoring as a new vote can show differences that were not shown in the previous scoring - it is like zooming in on the policy space and scoring again. 
When the winning proposal’s prediction dates are reached, their outcomes are evaluated by voters and voters only, whereby they vote by approval voting. Based on the result of the evaluation at a given time, the majority pick will update the prediction scores accordingly to some updating function. 

An example of the entire process: 
  - A poll is created with the name “How should we spend our marketing money?” and the subject area “marketing”.
  - Proposals are created such as “Spend all of the marketing money on Facebook ads”. 
  - Predictions are created such as “If all money is spent on Facebook ads we will get 1000 people to click this link on our page before 6/17/2024”.
  - Prediction bets are carried out like “I am 0.9 sure that the above prediction will come true if the proposal passes”.
  - Then the voting begins, the delegate's scoring is locked-in before the voting ends, and the result is calculated. If the above proposal won, predictions about it like the one above would be evaluated at its inputted date, which in this case is 6/17/2024.  

Flowback will recommend delegates per subject area that seem to be value-aligned, and the more value-aligned the higher up in the suggested order. Predictors and delegates might even be subscribed to with notifications for what they do.  

Flowback has further modules such as accounting and a Kanban board and schedule per group designed so that users of Flowback can get all of their designated tasks in their own Kanban board and meetings in their schedule. We have further integrated Jitsi for video conferences, admins can send mails, handle privileges in a group, put in the subject areas, and documents can be handled as well. It is important to have such modules as a decision needs to be implemented by some set of agents. Flowback also becomes an enterprise resource planning tool in this way, not only to decide but also to help with implementation. 


*Problems addressed*

Because we order things in Flowback after their interactions and make sure that items that will be decided on cannot slip by without notifications, it also makes Flowback robust to irrelevance - which is what trolls and spam usually rely on. 

If predictors try to game the system they could: together bet on predictions that are irrelevant and create such predictions, but such a colluding group needs to have some predictor that bets against them, meaning that they lose the colluding groups impact - and the more so the more times they collude. Predictors colluding on large scales becomes unlikely if transparent algorithms are actively supported in as many areas as possible. 

The subject areas could be voted on in a gaming way, but the largest group will always win there, and they can lose more from not having accurate subject areas in most cases as they are the largest group either way. 

There are various possible issues where their frequency and degree of negative impact should be measured by examining many trials with larger groups to get significant results. 


Predictive liquid democracy


The following describes predictive liquid democracy. Combining prediction markets and liquid democracy into predictive liquid democracy was done theoretically, and independently, by me ('independently' if someone else may have stated its properties, see 'Föreningen för Digital Demokrati' in Sweden - that is the association for Digital democracy - digitaldemocracy.world) when the Flowback project was in an early stage (2021). This decision system is anti-fragile, as it learns from any mistake if the mechanisms work well enough. Non-local delegation can be more optimal than local, where the locality is in regard to the network of social relations. It is possible that those who know many and seem knowledgeable are not and the result can become worse than it could be using a more objective recommendation algorithm for non-local delegation [8]. Predictive liquid democracy provides a base for such a recommendation algorithm. 

*Predictive liquid democracy as implemented in Flowback 2023-01*

Voter:
  - Can vote (with equal weight).
  - Has secret votes.
  - Can delegate temporally in any subject area as long as they want and prioritize these (if a poll would be in multiple subject areas, the delegate prioritized over the others is delegated to). They can also delegate to a delegate in all areas (that exist currently and will appear).
  - Can override their delegate by voting themselves or changing delegate before a poll deadline.
  - Can become or stop being a delegate.

Delegate:
  - Can vote (with the weight of delegations to them and possibly their own vote if they are a voter as well).
  - Has public votes.
  - Can not delegate (no meta-delegation, this may be changed based on empirical data).

Predictor:
  - Can create predictions (the outcome of one or more relevant variables until a specified time).
  - Can bet a probability on a prediction.
  - Has prediction scores (between 0 and 1, the interval can be made not to include 50\% by having it divided up in 5 for example with 20\% steps) based on how well they bet probabilities.
  - Predictors might be an artificial intelligence, an algorithm, or a human with an internal model for example. 

Poll:
  - Is a question where proposals are potential answers.
  - Is created by a poll creator.
  - Has one or more subject areas.
  - Has phases.

Poll phase problems:
  - The last second problem: if there is some item that can be added and should possibly be interacted with as well during a phase, then if a set of items are added too close to the end of a phase it can hinder others from interacting with it.
  - To solve the last second problem, the addition of an item central to a poll requires a separate poll phase. 
  - The removal problem: if everyone should not input a copy of an item to make sure the item exists at an upcoming phase, then it cannot be removed too close to the end of a phase.
  - To solve the removal problem, removal can be prohibited. 
  - It is possible to allow predictions, prediction probability bets and voting from a previous phase and still solve the last second problem. 
  - In order for delegates to interact minimally with each phase and to provide as much information as possible, no interaction may happen before its phase, for example betting happening during the prediction phase.

Separate poll phases: 
  - First phase: proposals can be inputted by proposal creators. Subject areas for polls are voted on (see subject area division). 
  - Second phase: proposals can no longer be inputted. Predictions can be inputted by predictors.
  - Third phase: predictions can no longer be inputted. Prediction probability bets can be inputted by predictors
  - Fourth phase: prediction probability bets can no longer be inputted. Voters and delegates can vote by inputting scores. 
  - Proposal scores determine a proposals position in the proposal list displayed, where a higher score means higher up and vice versa.
  - Fifth phase: delegates votes are locked.
  - Sixth phase: the result is calculated. 

Poll creator:
  - Can create but not edit or delete a poll.

Proposal creator:
  - Can create but not edit or delete a proposal.

Result:
  - The winners are the proposals with the highest average score.
  - There is one or more winners.
  - If there has been a previous vote with a tie a random proposal wins with equal probability, otherwise the poll goes back to the third period with only the winning proposals.

Prediction evaluation:
  - Prediction scores (which are in the subject areas chosen) are updated based on a prediction after its prediction specified time is reached.
  - The voters can vote yes or no (approval voting) if it occurred or not after the time and change their votes dynamically without an end time. The majority decided which alternative wins, which is the evaluation of the prediction.
  - It is always updated in such a way that no predictor can choose not to make certain prediction bets and gain a higher or keep the same prediction score as a result from it. This means that a predictor making any prediction bet on one proposal on a poll (if it was in general they would never be able to take a break) will have to make prediction bets for all of them or otherwise lose points from their prediction score. 
  - To make sure predictors do not need to make prediction bets on predictions that are clearly one way or the other, they can make them on predictions where there have been prediction bets that 1) differ (otherwise they can gain score by predicting things that everyone agrees upon) and 2) have a number of predictors with high enough prediction scores that have previously made prediction bets on the given prediction. 
  - Predictions are ordered by the sum of the predictors prediction scores that bet on it, the more the higher up, and higher if there has been a counter bet.

Prediction evaluation problems: 
  - The colluding predictor problem: what if some subset of predictors bet in a way such that they are differing and with high enough prediction scores during "the last second" so that others are lowered relative to theirs? 
  - The colluding predictor problem is improbable to create an asymmetry this way with a large set (more improbable the more members), correct bets give more positive and incorrect bets give more negative to the prediction scores so that this is normalized over time if it does happen, and finally a predictor can take such possibilities into account and can fully block such happenings by betting on everything. 
  - The irrelevant prediction problem: what if some subset of predictors add predictions that are irrelevant to the poll or the subject area? This question will be discussed later.

Subject area division:
  - Division of subject areas can be done by a hyper subject area that works to optimize the division of the other subjects continuously. If only one subject area is shown to be the best, then the hyper subject area can be merged into that subject area then being for everything. 
  - The subject area tree, where more specialization is deeper down the tree, is therefore pruned or added to in order to find subject areas with stable prediction scores.
  - Stable prediction scores require the extraction of stable patterns before the event in the subject area. 
  - The subject areas for a poll are voted on by voters with approval voting, and all of the positively scored subject areas over some threshold apply. Prediction scores in all those areas are updated at the prediction evaluation. This is during the proposal phase. 

Shared roles:
  - Everyone in the group considered is a poll creator, proposal creator, and predictor.

Delegates track record:
  - The history of delegates can be viewed and be commented on by anyone.

Poll quorum:
  - A percentage for how many votes need to be cast can be set as a percentage or number.

How can we ensure strategic voting not creating too large negative effects:
  - This is an empirical question which needs to be tested, even when the assumptions for when this works the best fail to be true to a larger degree, the real world outcomes might not become too negative more often or to such a degree that it is worse than a given current system.
  - It is possible to vote on goals as well, but it does not ensure that participants will not try to strategy vote if their goal is not chosen. When voting on goals, predictions are about the possible implications of the goals. 

*The properties of predictive liquid democracy*

A Condorcet jury is a jury where the following is the case:
  - The members of the jury has a probability of over 0.5 to pick a proposal in the set of optimal proposals (regarding a given goal).
  - The members of the jury are independent (in the sense of their probabilities of picking the proposal above being independent).

Properties of a Condorcet jury:
  - According to Condorcet’s jury theorem, as the size of the jury grows, the probability that an optimal proposal is chosen converges to 1 given a majority rule decision (plurality voting) as the size is larger and as it goes to infinity [9]. Condorcet's theorem is originally only for two alternatives, it can be extended to multiple alternatives and is conjectured to hold in the same way and has been proven to do so as the size goes to infinity [10] [11]. This will still be referred to as Condorcet's theorem but is implicitly Condorcet's theorem with extensions.  
  - There can be Condorcet juries in various subject areas that can be delegated to. 

Optimal sets: 
  - The optimal predictor set (in a subject area) is the set of predictors with the highest prediction score, which needs to be over 0.5. 
  - The optimal proposal voting set is the set of proposal votings predicted to be optimal by a predictor in the optimal predictor set with regard to the given goal. 
  - The optimal delegate set is the set of delegates voting on the optimal proposal voting set. 

Properties of optimal delegates:
  - It is trivially optimal, based on the information internal to the forum, to delegate to an optimal delegate with regard to a given goal such that it is uniformly delegated. 
  - The set of independent optimal delegates make up a Condorcet jury. 
  - Delegates track record can be checked by the members to check the alignment between the values they claim they have and how they vote given the predictions. This is the way to ensure goal-alignment to some degree. 

A perfect delegate case:
  - A shared goal between all voters, predictors, and delegates.
  - Every voter delegates to an independent delegate in the optimal delegate set. 
  - Delegates are rational based on their information. 
  - Delegates know other delegates are rational based on their information, and know about predictive liquid democracy and its properties as described. 

Properties of score voting: 
  - Allows for scores to correspond to probabilities, which can create a shared understanding of what the scores mean. 
  - Given a perfect delegate case, delegates will vote honestly with score voting, and the average of the scores for every proposal will be the best estimator for the proposal being optimal.
  - The no favorite betrayal criterion is satisfied meaning that the perceived best set of proposals are always scored to the highest by a rational voter. The perceived worst set of proposals are always scored lowest by a rational voter. Strategic voting may occur among the middle proposals when there is not a shared goal.  

Considering strategic voting using score voting: 
  - It has been shown that the strong Nash equilibrium is the Condorcet winner if voters vote strategically and have full information about what the other voters are going to vote for [12].
  - It is possible to have a prediction market about the strategic voting that is stable to some degree. 
  - Allowing voters to score delegates if there is not a shared goal is not good, because such scoring could easily be strategic.

Optimization outside of predictive liquid democracy:
  - Honesty and other factors can possibly be optimized toward outside the scope of predictive liquid democracy.
  - A recommendation mechanism for delegates can be implemented that recommends delegates based on value-alignment by some non-voting based measurement of that (as voting against a delegate with a certain value will happen otherwise). It should not be based on prediction scores in any way as the two are not related. 

Empirical questions:
  - How can we measure how good the system does? One measure is how well it finds a given ground truth, but otherwise? By the utility of the members over time perhaps, but how? Further, can we measure the degree of honesty?
  - How much does strategic voting affect the system negatively in reality? Is there another voting method that does better than score voting?  
  - How much does the predictor collusion problem and irrelevant predictions affect the system negatively in reality? In relation to the collusion problem, how can the prediction score thresholds be set? And how large should the penalty of not betting on one or more be to get the best result?
  - Which recommendation mechanism leads to the best outcome?
  - Which prediction scoring rule is the best one to use? The Brier score is one possibility, but it becomes inadequate for too frequent or rare events [13]. And what interval should be used with it?
  - Is the subject area division gamed? What should the threshold be at?
  - What are the ideal times of the phases?
  - Is anything gained from allowing meta-delegation?
  - Should we add an "irrelevant" alternative for predictions when betting or evaluating? Or will they sort themselves out in the suggested system?
  - Does predictive liquid democracy in action lead to a higher chance to find a given ground truth compared to other systems? In what contexts?
  - In general how do we optimize the system toward the factors making the system work the best?
  - How would betting on predictions with money change the system?

The largest organization possible may decide that a more local region can take certain decisions themselves while the super organization audits and can intervene at any time. This is because the largest organization is more probable to find the "correct answer" using predictive liquid democracy.



[1]: Hagberg, L. (2023). Collected papers on finitist mathematics and phenomenalism: a digital phenomenology. BoD-Books on Demand.

[2]: Lührmann, Anna; Lindberg, Staffan I. (2019). "A third wave of autocratization is here: what is new about it?".

[3]: V-Dem report 2021: Global wave of autocratization accelerates, Stefan Kalberer, 14. Mar 2021

[4]: Beckman, L., \& Mörkenstam, U. (2016). Politisk teori. Liber.

[5]: Carroll, Lewis (1884). The Principles of Parliamentary Representation. London: Harrison and Sons.

[6]: "Demoex (Sweden)". newDemocracy. The newDemocracy Foundation. Retrieved 23 April 2018.

[7]: Seeley, T.D. (2011). Honeybee democracy. Princeton University Press.

[8]: Kahng, A., Mackenzie, S., \& Procaccia, A. (2021). Liquid democracy: An algorithmic perspective. Journal of Artificial Intelligence Research, 70, 1223-1252.

[9]: De Condorcet, N. (2014). Essai sur l'application de l'analyse à la probabilité des décisions rendues à la pluralité des voix. Cambridge University Press.

[10]: List, C., \& Goodin, R. E. (2001). Epistemic democracy: Generalizing the Condorcet jury theorem.

[11]: Dietrich, F., \& Spiekermann, K. (2021). Jury theorems.

[12]: Laslier, J. F. (2006). Strategic approval voting in a large electorate.

[13]: Benedetti, R. (2010). Scoring rules for forecast verification. Monthly Weather Review, 138(1), 203-211.


