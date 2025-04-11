# Flowback Backend

## About

Flowback was created and project lead by Loke Hagberg. The co-creators of this version were:
Siamand Shahkaram, Emil Svenberg and Yuliya Hagberg.
It is a decision-making platform.

<sub><sub>This text is not allowed to be removed.</sub></sub>

## Installation

### Docker Compose
To run Flowback backend using Docker Compose, follow these instructions: 
1) [Download](https://github.com/Gofven/flowback/archive/refs/heads/master.zip) or [Clone](https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository) this repository to your local computer
2) Download [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows, macOS and Linux) or [Docker Compose](https://docs.docker.com/compose/install/linux/) (Linux)
3) Navigate to the root of this repository.
4) Run `docker compose up -d`
5) Flowback backend should now be accessible (by default on http://localhost:8000)

#### Documentation
You can find the api documenation at http://127.0.0.1:8000/schema/redoc/ once you have started the backend with docker.

#### Create admin account
To create an admin account that can be used in the frontend you will need to execute a command inside the backend docker container. By default, the container name is `<flowback_root_folder_name>-flowback-backend-1`.

You can enter the container through the docker desktop app, click on the container and then click on the terminal tab. There you can create an admin account by executing: 
```python
python manage.py createsuperuser
```

Alternatively, you can access the docker container by running the following command:
```
docker exec -ti <container_name> bash
```

And once you're inside the container, create an admin account using:
```python
python manage.py createsuperuser
```

#### About .env
When docker compose is running, it'll create .env file in the repository folder if it doesn't exist,
or append `DJANGO_SECRET` to the file if .env exists and the variable isn't present in it. 
If you wish to change the environment variables, use .env.example as reference!

### Caddy DNS Setup Example

After installing flowback, if you wish to configure Caddy as a reverse proxy for running Flowback on port 8000,
follow these steps:

1) Install Caddy by following the instructions from the [official Caddy website](https://caddyserver.com/docs/install).
2) Create a `Caddyfile` in the directory where you want to manage your Caddy server or use the default configuration
   directory (commonly `/etc/caddy` on Linux) with the following content:

    ```plaintext
    example.com {
        reverse_proxy :8000
        reverse_proxy /admin* :8000
        reverse_proxy /openid* :8000
        route /media* {
                uri strip_prefix /media
                root * /path/to/flowback_root/media
                file_server
        }
        route /static* {
                uri strip_prefix /static
                root * /path/to/flowback_root/static
                file_server 
        }
    }
   
    ```

   Replace `example.com` with your domain where you wish to host Flowback. If you're not using a
   custom domain, you can use localhost for local testing.

3) If you're using DNS for your domain, update your DNS records:
    - Add an **A record** pointing your domain (`example.com`) to your server's IP address.

4) Reload the Caddy service:
      ```bash
      sudo caddy reload --config /etc/caddy/Caddyfile
      ```

5) Ensure port 80 (HTTP) and port 443 (HTTPS) are open in your firewall and that your server allows incoming traffic on
   these ports.
   
6) Be sure to include your domain in the `ALLOWED_HOSTS` variable in your env, e.g. `ALLOWED_HOSTS="example.com"`

7) Access Flowback backend at your domain URL using HTTPS (e.g., `https://example.com`). Caddy automatically provisions
   an SSL certificate via Let's Encrypt.

For further customization, refer to the [Caddy documentation](https://caddyserver.com/docs/caddyfile).


## Content

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

The following is from Collected papers on finitist mathematics and phenomenalism: a digital phenomenology by Loke Hagberg 2023 [1] and Predictive Liquid Democracy by Loke Hagberg and Samuel Färdow Kazen [2].

## How the backend is built 

The Flowback backend is built with Python using the Django Rest Framework. 

The Django Rest Framework styleguide used is: https://github.com/HackSoftware/Django-Styleguide

The databases used are PostgreSQL, Redis and RabbitMQ. 

Redis is used for messaging in chats. 

RabbitMQ is used for scheduling non-chat notifications. 

## References: 

[1]: Hagberg, L. (2023). Collected papers on finitist mathematics and phenomenalism: a digital phenomenology. BoD-Books on Demand.

[2]: Hagberg, L., & Kazen, S. F. Predictive Liquid Democracy1. URL=<https://www.researchgate.net/publication/377557844_Predictive_Liquid_Democracy>
