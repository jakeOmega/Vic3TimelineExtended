"""Generate localization YAML files for Victoria 3 mod events.

Produces localization files for extra_law_events and ministry_law_events
with UTF-8 BOM encoding.

Usage:
    python gen_loc_files.py    # Generate localization files
"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOC_DIR = os.path.join(BASE_DIR, "localization", "english")

FILES = {
    "extra_law_events_l_english.yml": r"""l_english:

 #
 # Extra Law Enactment Events
 #

 # ===== 1 – The Bankers' Lobby (Financial Regulation) =====
 extra_law_events.1.t:0 "The Bankers' Lobby"
 extra_law_events.1.d:0 "Our proposed reforms to the financial sector have drawn the attention of powerful banking interests. The [SCOPE.gsInterestGroup('opposing_ig').GetName] have dispatched a delegation of well-dressed men to the halls of government, armed with ledgers full of dire predictions about the consequences of [SCOPE.sLaw('current_law_scope').GetName]."
 extra_law_events.1.f:0 ""You must understand, gentlemen, that if you proceed with this legislation, you will be sawing through the very branch upon which the prosperity of this nation sits. We are not here to threaten — merely to illuminate the consequences of haste.""
 extra_law_events.1.a:0 "We shall hear their concerns, but the reform proceeds."
 extra_law_events.1.b:0 "Build a broader coalition — hear the bankers out."

 # ===== 2 – A Run on the Banks (Financial Regulation) =====
 extra_law_events.2.t:0 "A Run on the Banks"
 extra_law_events.2.d:0 "A wave of panic has swept through the financial houses as depositors, alarmed by rumors about the coming regulatory changes, have begun withdrawing their savings. Queues stretch around the block at several major institutions."
 extra_law_events.2.f:0 ""I asked the teller for my money and he had the audacity to tell me to come back next week! Next week! By then these new laws will have turned my savings into wallpaper!""
 extra_law_events.2.a:0 "This proves exactly why we need stronger regulation!"
 extra_law_events.2.b:0 "Calm the markets first, then proceed carefully."

 # ===== 3 – The Gold Question (Monetary Policy) =====
 extra_law_events.3.t:0 "The Gold Question"
 extra_law_events.3.d:0 "A heated debate has erupted over our proposed monetary reforms. The [SCOPE.gsInterestGroup('opposing_ig').GetName] have rallied behind the old monetary order, arguing that abandoning it will bring ruin upon the nation's finances."
 extra_law_events.3.f:0 ""You shall not press down upon the brow of labor this crown of gold! You shall not crucify mankind upon a cross of metal! The wealth of a nation is measured in its industry, not in bars locked away in a vault.""
 extra_law_events.3.a:0 "The old monetary order must give way to progress."
 extra_law_events.3.b:0 "Bring the opposition into the conversation."

 # ===== 4 – The Printing Press of Money (Monetary Policy – Fiat) =====
 extra_law_events.4.t:0 "The Printing Press of Money"
 extra_law_events.4.d:0 "Advocates of the new fiat currency system have made a compelling case before the legislature: the ability to control the money supply will allow the government to smooth out the devastating boom-and-bust cycles that have plagued the nation."
 extra_law_events.4.f:0 ""The gold bugs would have us chained to a lump of metal dug from the earth, when the true wealth of a nation flows from the creativity and labor of its people. Give me a printing press and I shall give you full employment!""
 extra_law_events.4.a:0 "The power to print is the power to prosper!"
 extra_law_events.4.b:0 "Build an academic consensus first."

 # ===== 5 – The Wiretapping Scandal (Privacy Rights) =====
 extra_law_events.5.t:0 "The Wiretapping Scandal"
 extra_law_events.5.d:0 "A journalist has published a damning exposé revealing that government agents have been intercepting the private correspondence of ordinary citizens. The revelations have ignited a fierce public debate about the proper limits of state surveillance."
 extra_law_events.5.f:0 ""They read my letters to my mother. My mother! And for what? Because I once attended a lecture by a man who attended a lecture by a man the police found suspicious? This is not security — this is tyranny dressed in a clerk's coat.""
 extra_law_events.5.a:0 "This outrage proves the need for our proposed law!"
 extra_law_events.5.b:0 "Proceed quietly — don't overplay our hand."
 extra_law_events.5.c:0 "Frame it as a security matter and force the issue."

 # ===== 6 – The Viral Campaign (Internet Governance) =====
 extra_law_events.6.t:0 "The Viral Campaign"
 extra_law_events.6.d:0 "A grassroots campaign organized by the [SCOPE.gsInterestGroup('supporting_ig').GetName] has gone viral across the nation's digital networks, generating enormous public interest in our proposed [SCOPE.sLaw('current_law_scope').GetName] legislation."
 extra_law_events.6.f:0 ""It started as a single post on a message board, and within forty-eight hours it had been shared by millions. The old guard doesn't understand: you cannot put the genie of information back in the bottle.""
 extra_law_events.6.a:0 "Ride the wave — let the campaign build pressure."
 extra_law_events.6.b:0 "Channel the energy into a measured public consultation."

 # ===== 7 – The Ethics of the Gene (Genetic Rights) =====
 extra_law_events.7.t:0 "The Ethics of the Gene"
 extra_law_events.7.d:0 "The proposed changes to our genetic legislation have sparked a furious moral debate. The [SCOPE.gsInterestGroup('devout_ig').GetName] have organized public sermons denouncing the 'arrogance of man,' while scientists plead for the freedom to pursue breakthroughs that could end hereditary disease."
 extra_law_events.7.f:0 ""To rewrite the very code of life written by the Almighty is to commit the sin of Prometheus. But then, Prometheus did bring us fire, and we have yet to return it.""
 extra_law_events.7.a:0 "Science must not be shackled by superstition!"
 extra_law_events.7.b:0 "Invite the clergy into the drafting process."

 # ===== 8 – The Robber Barons (Antitrust) =====
 extra_law_events.8.t:0 "The Robber Barons"
 extra_law_events.8.d:0 "Public anger has been building against the great industrial combines. Pamphlets circulate depicting the [SCOPE.gsInterestGroup('industrialists_ig').GetName] as bloated spiders sitting at the center of a web of monopoly, choking fair competition and gouging the common consumer."
 extra_law_events.8.f:0 ""The great trusts have turned the marketplace into a private fiefdom. Where once a hundred firms competed, now one baron sits upon a throne of steel and oil, and dares to call his extortion 'efficiency.'""
 extra_law_events.8.a:0 "The monopolists have had their day — break the trusts!"
 extra_law_events.8.b:0 "Negotiate a compromise with industry."

 # ===== 9 – The Pirate's Dilemma (Intellectual Property) =====
 extra_law_events.9.t:0 "The Pirate's Dilemma"
 extra_law_events.9.d:0 "Our proposed changes to intellectual property law have split the [SCOPE.gsInterestGroup('intelligentsia_ig').GetName]. Some argue passionately that ideas are the common heritage of mankind, while others insist that without the protection of patents, the wellspring of invention will dry up."
 extra_law_events.9.f:0 ""If I plant an apple tree, the apples are mine. But if I sing a song, does it not belong to everyone who hears it? The question of who owns an idea is, I suspect, the question that will define this century.""
 extra_law_events.9.a:0 "The reform is long overdue — pass it now!"
 extra_law_events.9.b:0 "Build an academic consensus with the intelligentsia."

 # ===== 10 – Reports from the Front (Rules of War) =====
 extra_law_events.10.t:0 "Reports from the Front"
 extra_law_events.10.d:0 "Harrowing accounts of battlefield atrocities have reached the newspapers, shocking the public conscience. Photographs of civilian suffering and descriptions of indiscriminate bombardment have galvanized support for the proposed [SCOPE.sLaw('current_law_scope').GetName] legislation."
 extra_law_events.10.f:0 ""I have seen things in the field that I shall carry to my grave. If the purpose of war is to defend civilization, then we must not abandon civilization in its prosecution. There must be lines that even the victorious dare not cross.""
 extra_law_events.10.a:0 "The civilized world demands restraint!"
 extra_law_events.10.b:0 "Build a bipartisan coalition for lasting reform."

 # ===== 11 – The Generals Object (Rules of War – Military Pushback) =====
 extra_law_events.11.t:0 "The Generals Object"
 extra_law_events.11.d:0 "Senior officers of the [SCOPE.gsInterestGroup('armed_forces_ig').GetName] have submitted a memorandum to the government protesting the proposed [SCOPE.sLaw('current_law_scope').GetName]. They argue that binding the hands of commanders in wartime will cost more lives than it saves."
 extra_law_events.11.f:0 ""With the greatest respect, gentlemen of the legislature have never held a field command. War is not a gentleman's game. If you tie our hands with these regulations, the enemy will not reciprocate, and it is our soldiers — not yours — who will pay the price.""
 extra_law_events.11.a:0 "Overrule the generals — this is a matter of principle."
 extra_law_events.11.b:0 "Accommodate their concerns to keep them on side."

 # ===== 12 – A Question of Punishment (Criminal Justice) =====
 extra_law_events.12.t:0 "A Question of Punishment"
 extra_law_events.12.d:0 "A prominent member of the [SCOPE.gsInterestGroup('intelligentsia_ig').GetName] has published a treatise arguing that the purpose of the justice system should not be vengeance, but the restoration of the offender to productive membership in society."
 extra_law_events.12.f:0 ""The man who emerges from our prisons today is harder, angrier, and less capable of honest work than the day he entered. We have built factories of recidivism and called them houses of justice. There must be a better way.""
 extra_law_events.12.a:0 "Rehabilitation is the mark of a civilized nation."
 extra_law_events.12.b:0 "Frame it as tough-on-crime reform to win over the skeptics."

 # ===== 13 – Tongues of the Nation (Language Policy) =====
 extra_law_events.13.t:0 "Tongues of the Nation"
 extra_law_events.13.d:0 "Our proposed language reforms have met fierce resistance from the [SCOPE.gsInterestGroup('opposing_ig').GetName], who see the legislation as an assault on the cultural identity of communities across the nation."
 extra_law_events.13.f:0 ""A language is not merely a tool for commerce. It is the vessel of a people's history, their songs, their prayers, their very soul. To legislate it away is to commit a quiet kind of murder.""
 extra_law_events.13.a:0 "A common tongue strengthens national unity."
 extra_law_events.13.b:0 "Make concessions to the periphery to ease passage."

 # ===== 14 – A Donor Scandal (Electoral Finance) =====
 extra_law_events.14.t:0 "A Donor Scandal"
 extra_law_events.14.d:0 "An investigation has revealed that several prominent politicians received lavish gifts and secret payments from wealthy donors in exchange for favorable legislation. The public is outraged, and reformers are seizing the moment to push for [SCOPE.sLaw('current_law_scope').GetName]."
 extra_law_events.14.f:0 ""The honorable member's vote, it seems, was not so much cast as it was purchased. One wonders if the legislature might save time by simply auctioning off its seats to the highest bidder.""
 extra_law_events.14.a:0 "Expose the corruption and push for reform!"
 extra_law_events.14.b:0 "Use this quietly as leverage — no need for spectacle."

 # ===== 15 – The Question of Autonomy (State Power) =====
 extra_law_events.15.t:0 "The Question of Autonomy"
 extra_law_events.15.d:0 "A petition signed by regional leaders and local dignitaries has arrived at the capital, either demanding greater autonomy for the provinces or insisting on stronger central authority. The debate over [SCOPE.sLaw('current_law_scope').GetName] has become a lightning rod for longstanding tensions."
 extra_law_events.15.f:0 ""The question is not merely one of administration, but of identity. Does a citizen owe loyalty first to the province that raised him, or to the nation that protects him? The answer to this question will shape our republic for generations.""
 extra_law_events.15.a:0 "Our proposed reform will settle this question."
 extra_law_events.15.b:0 "Allow the regions a voice in the drafting process."

 # ===== 16 – The Augmentation Hearing (Human Augmentation) =====
 extra_law_events.16.t:0 "The Augmentation Hearing"
 extra_law_events.16.d:0 "A parliamentary committee has convened to hear testimony on the proposed [SCOPE.sLaw('current_law_scope').GetName] legislation. Scientists from the [SCOPE.gsInterestGroup('intelligentsia_ig').GetName] present dazzling demonstrations, while members of the [SCOPE.gsInterestGroup('devout_ig').GetName] warn of a society divided between the enhanced and the natural."
 extra_law_events.16.f:0 ""The witness removed his glove to reveal a hand of articulated steel, each finger moving with uncanny precision. 'I lost the original in a factory press,' he said. 'The replacement is better. The question before you today is simple: should the rest of me be allowed to catch up?'""
 extra_law_events.16.a:0 "Progress demands that we push the boundaries!"
 extra_law_events.16.b:0 "Appoint an ethics board to reassure the public."

 # ===== 17 – The Eldest Son's Complaint (Inheritance) =====
 extra_law_events.17.t:0 "The Eldest Son's Complaint"
 extra_law_events.17.d:0 "The proposed changes to inheritance law have provoked outrage among the [SCOPE.gsInterestGroup('landowners_ig').GetName]. The eldest sons of several prominent families have petitioned the government, warning that dividing their estates will destroy the great houses that form the backbone of rural society."
 extra_law_events.17.f:0 ""My father built this estate with his own hands, and his father before him. Now you tell me I must share it equally with my younger brothers, one of whom has not visited in five years and the other of whom is a notorious gambler? This is not justice — this is vandalism.""
 extra_law_events.17.a:0 "All children deserve an equal share."
 extra_law_events.17.b:0 "Offer a transition period to ease the landowners' fears."

 # ===== 18 – Petitions of the Heart (LGBTQ Rights) =====
 extra_law_events.18.t:0 "Petitions of the Heart"
 extra_law_events.18.d:0 "A group of citizens has delivered a moving petition to the legislature, sharing personal stories of discrimination and asking for the protections promised by [SCOPE.sLaw('current_law_scope').GetName]. The petition has generated significant public sympathy, though the [SCOPE.gsInterestGroup('devout_ig').GetName] have denounced it."
 extra_law_events.18.f:0 ""We do not ask for special treatment. We ask only to walk the same streets, hold the same jobs, and love the same as any other citizen of this nation, without fear of the magistrate's knock upon the door.""
 extra_law_events.18.a:0 "The petitioners shall be heard — their cause is just."
 extra_law_events.18.b:0 "Work quietly behind the scenes to defuse opposition."

 # ===== 19 – The Cradle and the State (Family & Reproductive Policy) =====
 extra_law_events.19.t:0 "The Cradle and the State"
 extra_law_events.19.d:0 "Our proposed changes to family policy have ignited a passionate debate. Supporters argue that the demographic future of the nation hangs in the balance, while opponents insist that the bedroom is no place for the heavy hand of the state."
 extra_law_events.19.f:0 ""The nation that cannot replace its population is a nation in twilight. But the nation that dictates the most intimate decisions of its citizens is a nation that has forgotten what it is fighting to preserve.""
 extra_law_events.19.a:0 "The demographic future of the nation is at stake!"
 extra_law_events.19.b:0 "Frame it as supporting families to build consensus."

 # ===== 20 – The Whistleblower (Right to Information) =====
 extra_law_events.20.t:0 "The Whistleblower"
 extra_law_events.20.d:0 "A mid-ranking government clerk has leaked a trove of classified documents to the press, revealing years of hidden malfeasance and waste. The timing could not be better for our push toward [SCOPE.sLaw('current_law_scope').GetName], though the establishment is furious."
 extra_law_events.20.f:0 ""I knew what I was risking when I walked into that newspaper office. But I also know what it costs a nation when its government operates in the dark. Sunlight, they say, is the best disinfectant.""
 extra_law_events.20.a:0 "The people have a right to know!"
 extra_law_events.20.b:0 "Manage the revelations carefully to avoid chaos."
 extra_law_events.20.c:0 "Use the leaks as leverage to silence the opposition."

 # ===== 21 – A March for Dignity (Minority Rights) =====
 extra_law_events.21.t:0 "A March for Dignity"
 extra_law_events.21.d:0 "Thousands of citizens have taken to the streets in a peaceful march demanding equal rights and protections under [SCOPE.sLaw('current_law_scope').GetName]. The procession stretches through the heart of the capital, drawing international attention."
 extra_law_events.21.f:0 ""They marched in silence for the first mile. Then someone began to sing, and by the time they reached the steps of the legislature, ten thousand voices carried the melody. It was, by any measure, the most powerful argument ever made without a single word of debate.""
 extra_law_events.21.a:0 "March with them — show the world we are changing!"
 extra_law_events.21.b:0 "Support the cause from the legislature floor."

 # ===== 22 – The Automation Question (Welfare – UBI / Post-Scarcity) =====
 extra_law_events.22.t:0 "The Automation Question"
 extra_law_events.22.d:0 "The relentless march of automation has left thousands without work, and the [SCOPE.gsInterestGroup('trade_unions_ig').GetName] are demanding radical action. Proponents of [SCOPE.sLaw('current_law_scope').GetName] argue that when machines do the work, the bounty must be shared with all."
 extra_law_events.22.f:0 ""The loom does not eat. The steam-hammer does not sleep. The calculating engine does not demand a pension. And yet the men they replaced must still feed their families. If the machines have taken the work, then the machines must pay the wages.""
 extra_law_events.22.a:0 "The machines free us — we must share the bounty!"
 extra_law_events.22.b:0 "Phase it in gradually to win over industry."

 # ===== 23 – The Algorithmic Showcase (Governance – Algorithmic) =====
 extra_law_events.23.t:0 "The Algorithmic Showcase"
 extra_law_events.23.d:0 "Proponents of algorithmic governance have organized a dramatic public demonstration, allowing a prototype system to allocate a city's budget in real time. The results are impressive — eliminating waste, optimizing services, and doing it all in minutes rather than months."
 extra_law_events.23.f:0 ""The machine does not accept bribes. It does not favor one district over another because of a cousin's connections. It simply calculates the optimal outcome and executes it. Whether this is liberation or damnation, I confess, I cannot yet tell.""
 extra_law_events.23.a:0 "The demonstration speaks for itself — forge ahead!"
 extra_law_events.23.b:0 "Build public understanding before proceeding."

 # ===== 24 – The People's Assembly (Governance – Direct Democracy) =====
 extra_law_events.24.t:0 "The People's Assembly"
 extra_law_events.24.d:0 "A mass gathering of citizens has spontaneously organized in the capital's central square, debating policy and passing informal resolutions by show of hands. The [SCOPE.gsInterestGroup('opposing_ig').GetName] view this spectacle with alarm, but supporters of [SCOPE.sLaw('current_law_scope').GetName] see it as proof that the people are ready to govern themselves."
 extra_law_events.24.f:0 ""For a single afternoon, the square was not a marketplace but a parliament. Fishmongers debated with professors, and the vote of a seamstress carried the same weight as that of a factory owner. It was, depending upon one's disposition, either the dawn of a new age or the beginning of the end.""
 extra_law_events.24.a:0 "Ride the popular wave — push the reform through!"
 extra_law_events.24.b:0 "Bring the opposition into the process."
""",

    "ministry_law_events_l_english.yml": r"""l_english:

 #
 # Ministry Law Enactment Events
 #

 # ===== 1 – Staffing the New Ministry (Generic – Establishing) =====
 ministry_law_events.1.t:0 "Staffing the New Ministry"
 ministry_law_events.1.d:0 "The government has begun the enormous task of standing up [SCOPE.sLaw('current_law_scope').GetName]. Advertisements for clerks, administrators, and departmental heads have been posted across every public notice board, and a flood of applications — some qualified, many spectacularly not — has poured in."
 ministry_law_events.1.f:0 "The new ministry shall require, at minimum, fourteen senior administrators, forty-two departmental heads, two hundred and seven clerks, and — if the budget permits — a reliable doorman. I trust these positions will be filled strictly on merit, which is to say, by the cousins of those already appointed."
 ministry_law_events.1.a:0 "Recruit aggressively — fill every desk."
 ministry_law_events.1.b:0 "Staff it gradually to ensure quality."

 # ===== 2 – The Budget Debate (Generic – Establishing) =====
 ministry_law_events.2.t:0 "The Budget Debate"
 ministry_law_events.2.d:0 "Parliament has erupted into heated argument over the proposed funding for [SCOPE.sLaw('current_law_scope').GetName]. The [SCOPE.gsInterestGroup('opposing_ig').GetName] insist the money would be better spent elsewhere, while proponents argue that the new ministry cannot function without proper resources."
 ministry_law_events.2.f:0 "The honorable member claims this ministry will cost a mere trifle. Allow me to remind him that the last 'trifle' we approved has consumed an entire wing of the treasury and shows no sign of producing anything more useful than memoranda addressed to other memoranda."
 ministry_law_events.2.a:0 "Allocate the full budget — half measures produce half results."
 ministry_law_events.2.b:0 "Promise a lean operation to win the skeptics over."

 # ===== 3 – Bureaucratic Turf Wars (Generic – Establishing) =====
 ministry_law_events.3.t:0 "Bureaucratic Turf Wars"
 ministry_law_events.3.d:0 "The creation of [SCOPE.sLaw('current_law_scope').GetName] has provoked a turf war among existing government departments. Senior officials who have managed these matters for years are reluctant to cede authority to a new ministry and its untested staff."
 ministry_law_events.3.f:0 "The permanent secretary looked as though I had asked him to hand over his firstborn child. 'You cannot simply take the Trade Division,' he said, clutching his files to his chest. 'I have been nurturing this department since before you were in Parliament.'"
 ministry_law_events.3.a:0 "Assert the new ministry's jurisdiction — clarity is essential."
 ministry_law_events.3.b:0 "Allow a transitional period to ease the change."

 # ===== 4 – The Redundant Clerks (Generic – Dissolving) =====
 ministry_law_events.4.t:0 "The Redundant Clerks"
 ministry_law_events.4.d:0 "With the proposed passage of [SCOPE.sLaw('current_law_scope').GetName], hundreds of government employees face the prospect of redundancy. The corridors of the soon-to-be-dissolved ministry are filled with anxious functionaries, their desks already half-packed, their futures uncertain."
 ministry_law_events.4.f:0 "Twenty-three years I have given to this ministry. Twenty-three years of filing, stamping, and indexing. And now they tell me my services are no longer required. I suppose I shall have to learn what it is that ordinary people do with their afternoons."
 ministry_law_events.4.a:0 "Swift dissolution is best — rip off the bandage."
 ministry_law_events.4.b:0 "Offer generous severance and retraining."

 # ===== 5 – The Generals' War Room (Ministry of War) =====
 ministry_law_events.5.t:0 "The Generals' War Room"
 ministry_law_events.5.d:0 "Senior officers of the [SCOPE.gsInterestGroup('armed_forces_ig').GetName] have submitted a pointed memorandum regarding the proposed [SCOPE.sLaw('current_law_scope').GetName]. They insist that military matters require military expertise, and that civilian bureaucrats have no business directing the affairs of war."
 ministry_law_events.5.f:0 "The Field Marshal was blunt: 'You may legislate all you wish about the procurement of boot-leather and the allocation of rations. But the moment a clerk in a morning coat presumes to tell me how to deploy a brigade, I shall tender my resignation and advise my officers to do the same.'"
 ministry_law_events.5.a:0 "Civilian oversight is non-negotiable."
 ministry_law_events.5.b:0 "Grant operational autonomy to ease the transition."

 # ===== 6 – The Ambassador's Dilemma (Ministry of Foreign Affairs) =====
 ministry_law_events.6.t:0 "The Ambassador's Dilemma"
 ministry_law_events.6.d:0 "A diplomatic incident with a foreign power has exposed the embarrassing inadequacy of our current foreign affairs apparatus. Communiqués were bungled, protocols were ignored, and the resulting misunderstanding nearly escalated into a crisis — lending fresh urgency to the case for [SCOPE.sLaw('current_law_scope').GetName]."
 ministry_law_events.6.f:0 "The ambassador, it transpires, greeted the foreign dignitary with the traditional salutation for a funeral rather than a state banquet. The dignitary was not amused. I am told relations have been set back by approximately a decade."
 ministry_law_events.6.a:0 "This debacle proves we need a proper ministry!"
 ministry_law_events.6.b:0 "Use the incident to build a careful consensus."

 # ===== 7 – The Merchant's Petition (Ministry of Commerce) =====
 ministry_law_events.7.t:0 "The Merchant's Petition"
 ministry_law_events.7.d:0 "A delegation of merchants and manufacturers, led by prominent members of the [SCOPE.gsInterestGroup('industrialists_ig').GetName], has presented a petition regarding [SCOPE.sLaw('current_law_scope').GetName]. They argue that the chaos of competing regulations and tariffs is strangling commerce, and that a coordinated ministry is essential."
 ministry_law_events.7.f:0 "I must apply to three different offices to export a single crate of textiles. The first grants me a permit, the second demands a different permit, and the third informs me that both permits expired yesterday. A Ministry of Commerce would, at the very least, reduce the permits to one."
 ministry_law_events.7.a:0 "Commerce demands coordination — push it through!"
 ministry_law_events.7.b:0 "Design the ministry to address merchant concerns."

 # ===== 8 – The Artist's Subsidy (Ministry of Culture) =====
 ministry_law_events.8.t:0 "The Artist's Subsidy"
 ministry_law_events.8.d:0 "The debate over [SCOPE.sLaw('current_law_scope').GetName] has drawn the nation's artists and intellectuals into a furious argument. Some in the [SCOPE.gsInterestGroup('intelligentsia_ig').GetName] welcome state patronage as the foundation of a cultural renaissance, while others see it as the first step toward censorship and conformity."
 ministry_law_events.8.f:0 "The poet stood before the committee and declared that he would sooner burn his manuscripts than submit them for government approval. The painter beside him quietly noted that government approval came with a very generous stipend, and asked where one might apply."
 ministry_law_events.8.a:0 "A great nation deserves a Ministry of Culture."
 ministry_law_events.8.b:0 "Let the artists help design it — win their support."

 # ===== 9 – Capital vs. Labor (Ministry of Labor – both variants) =====
 ministry_law_events.9.t:0 "Capital vs. Labor"
 ministry_law_events.9.d:0 "The proposed [SCOPE.sLaw('current_law_scope').GetName] has ignited the eternal struggle between capital and labor. Factory owners and workers' representatives have each mounted fierce campaigns, and the question of whose interests the new ministry will serve has become the dominant political issue of the season."
 ministry_law_events.9.f:0 "The factory owner slammed his fist on the table: 'A ministry that coddles workers will bankrupt us all!' The union leader replied without blinking: 'A ministry that coddles owners already exists — it is called the rest of the government.'"
 ministry_law_events.9.a:0 "The ministry will serve the national interest — press forward!"
 ministry_law_events.9.b:0 "Proceed carefully to minimize opposition."
 ministry_law_events.9.c:0 "Invite the key stakeholders to shape the ministry."

 # ===== 10 – The Smokestack Question (Ministry of the Environment) =====
 ministry_law_events.10.t:0 "The Smokestack Question"
 ministry_law_events.10.d:0 "The [SCOPE.gsInterestGroup('industrialists_ig').GetName] have mounted a vigorous campaign against [SCOPE.sLaw('current_law_scope').GetName], arguing that environmental regulation will cripple the nation's industry and cost thousands of jobs. Meanwhile, reports of poisoned rivers and blackened skies have galvanized public support."
 ministry_law_events.10.f:0 "The factory owner pointed at his smokestacks and declared them the engines of prosperity. The fisherman downstream pointed at his empty nets and called them the instruments of ruin. Both, I regret to say, were correct."
 ministry_law_events.10.a:0 "The environment cannot wait — industry must adapt!"
 ministry_law_events.10.b:0 "Offer industry a seat at the table."

 # ===== 11 – The Shadow Files (Ministry of Intelligence and Security) =====
 ministry_law_events.11.t:0 "The Shadow Files"
 ministry_law_events.11.d:0 "Leaked documents have revealed the extraordinary capabilities that [SCOPE.sLaw('current_law_scope').GetName] would grant to the state — surveillance networks, informant systems, and the power to operate beyond ordinary legal oversight. The public is uneasy, though some argue such tools are the price of security."
 ministry_law_events.11.f:0 "The leaked memorandum was clinical in its language: 'Full spectrum monitoring of communications, including private correspondence, shall be considered a standard operational capability.' The journalist who published it has since found it prudent to relocate abroad."
 ministry_law_events.11.a:0 "Security demands these tools — push forward."
 ministry_law_events.11.b:0 "Build in strict oversight to reassure the public."

 # ===== 12 – The Refugee Ship (Ministry of Refugee Affairs) =====
 ministry_law_events.12.t:0 "The Refugee Ship"
 ministry_law_events.12.d:0 "A ship carrying hundreds of displaced persons has arrived in our harbor, their homeland torn apart by war and famine. The sight of desperate families huddled on the docks has given urgency to the debate over [SCOPE.sLaw('current_law_scope').GetName]."
 ministry_law_events.12.f:0 "The woman held her infant up to the customs officer and said, in halting words he could barely understand, 'Please. This is all I have left.' Behind her, the queue stretched to the end of the pier."
 ministry_law_events.12.a:0 "A civilized nation does not turn away the desperate."
 ministry_law_events.12.b:0 "Frame it as an orderly process to ease domestic fears."

 # ===== 13 – The Loudspeaker State (Ministry of Propaganda) =====
 ministry_law_events.13.t:0 "The Loudspeaker State"
 ministry_law_events.13.d:0 "The proposal to establish [SCOPE.sLaw('current_law_scope').GetName] has sent a chill through the nation's newspaper offices and printing houses. Members of the [SCOPE.gsInterestGroup('intelligentsia_ig').GetName] fear that a ministry devoted to controlling information will transform the free press into a megaphone for the state."
 ministry_law_events.13.f:0 "The editor-in-chief received the proposed regulations and read them twice. Then he looked at his staff and said, 'Gentlemen, we have two choices: we can print what they tell us to print, or we can start looking for honest work.'"
 ministry_law_events.13.a:0 "The truth must be guided for the good of the people."
 ministry_law_events.13.b:0 "Rebrand it as public information to calm the press."

 # ===== 14 – The Laboratory of the State (Ministry of Science) =====
 ministry_law_events.14.t:0 "The Laboratory of the State"
 ministry_law_events.14.d:0 "A breakthrough at a university laboratory has reignited the debate over [SCOPE.sLaw('current_law_scope').GetName]. Members of the [SCOPE.gsInterestGroup('intelligentsia_ig').GetName] argue that only coordinated state investment can turn such discoveries into practical advances, while skeptics warn that bureaucrats make poor scientists."
 ministry_law_events.14.f:0 "The professor presented his findings with quiet pride. The parliamentarian beside me leaned over and whispered, 'Very impressive. Now, can it win a war?' I fear that is precisely the question the Ministry will be created to answer."
 ministry_law_events.14.a:0 "Science needs state coordination — push forward!"
 ministry_law_events.14.b:0 "Let the universities lead the design process."

 # ===== 15 – The Watchers (Ministry of Thought Control) =====
 ministry_law_events.15.t:0 "The Watchers"
 ministry_law_events.15.d:0 "Reports of underground resistance networks have given fresh ammunition to supporters of [SCOPE.sLaw('current_law_scope').GetName]. Pamphlets circulate in secret, suspicious meetings are held in cellars, and the authorities fear that dissent is spreading faster than it can be monitored."
 ministry_law_events.15.f:0 "The informant's report was terse: 'They meet every Thursday in the back room of the printer's shop. They read forbidden texts and discuss ideas that would make your blood run cold.' When asked what these ideas were, he admitted he hadn't actually attended a meeting, but had heard about them from another informant."
 ministry_law_events.15.a:0 "Dissent must be monitored for the nation's safety."
 ministry_law_events.15.b:0 "Start with modest powers to avoid a backlash."

 # ===== 16 – The Tainted Product (Ministry of Consumer Protection) =====
 ministry_law_events.16.t:0 "The Tainted Product"
 ministry_law_events.16.d:0 "A scandal has erupted after dozens of citizens fell ill from a contaminated product sold by a prominent manufacturer. The [SCOPE.gsInterestGroup('industrialists_ig').GetName] protest that it was an isolated incident, but investigators found that the company had been cutting costs at the expense of safety for years."
 ministry_law_events.16.f:0 "The label promised 'Pure and Wholesome.' The chemist's analysis found sawdust, chalk, and a substance he diplomatically described as 'of uncertain animal origin.' When confronted, the manufacturer protested that his competitors used far worse."
 ministry_law_events.16.a:0 "Consumers deserve protection — act now!"
 ministry_law_events.16.b:0 "Let industry self-regulate within the new framework."

 # ===== 17 – The City Rises (Ministry of Urban Planning) =====
 ministry_law_events.17.t:0 "The City Rises"
 ministry_law_events.17.d:0 "The nation's cities are growing at a pace that alarms even their most enthusiastic boosters. Tenements spring up overnight, sewage systems overflow, and the air grows thick with soot. The case for [SCOPE.sLaw('current_law_scope').GetName] has never been more urgent — or more controversial."
 ministry_law_events.17.f:0 "I walked through the new district this morning. In the space where a meadow stood last year, there are now fourteen tenement blocks, a factory, and precisely zero public parks. The developer assured me that a park was planned, but it kept being replaced by more profitable buildings."
 ministry_law_events.17.a:0 "Cities need plans, not chaos — establish the ministry!"
 ministry_law_events.17.b:0 "Consult with developers to smooth the transition."

 # ===== 18 – The Pulpit and the State (Ministry of Religion) =====
 ministry_law_events.18.t:0 "The Pulpit and the State"
 ministry_law_events.18.d:0 "The proposal for [SCOPE.sLaw('current_law_scope').GetName] has provoked a fierce reaction from the [SCOPE.gsInterestGroup('devout_ig').GetName]. Some clerics welcome state support as a means to spread the faith, while others fear that government involvement will turn the church into an instrument of political control."
 ministry_law_events.18.f:0 "The bishop's letter was measured: 'The church has survived empires, revolutions, and heresies without the assistance of a government ministry. We are not entirely certain we require one now. That said, if such a ministry were to include a generous building fund for cathedrals, we would be willing to hear the proposal in greater detail.'"
 ministry_law_events.18.a:0 "Faith and governance shall strengthen each other."
 ministry_law_events.18.b:0 "Promise clerical autonomy within the ministry."

 # ===== 19 – The Distant Crisis (Ministry of International Aid) =====
 ministry_law_events.19.t:0 "The Distant Crisis"
 ministry_law_events.19.d:0 "Reports of a devastating famine in a foreign land have filled the newspapers with harrowing images. Humanitarian organizations are pleading for the government to act, and supporters of [SCOPE.sLaw('current_law_scope').GetName] argue that a dedicated ministry is the only way to respond effectively to such crises."
 ministry_law_events.19.f:0 "The photograph showed a child with ribs like a birdcage, staring at the camera with enormous, uncomprehending eyes. It appeared on the front page of every major newspaper, and by noon the Prime Minister's office had received ten thousand letters demanding action."
 ministry_law_events.19.a:0 "A great nation has obligations to the world."
 ministry_law_events.19.b:0 "Frame it as strategic investment to win domestic support."
""",
}


def main():
    os.makedirs(LOC_DIR, exist_ok=True)

    for filename, content in FILES.items():
        filepath = os.path.join(LOC_DIR, filename)
        # Strip the leading newline from the raw string (artifact of triple-quote)
        if content.startswith("\n"):
            content = content[1:]
        # Ensure file ends with exactly one trailing newline
        content = content.rstrip("\n") + "\n"
        with open(filepath, "w", encoding="utf-8-sig", newline="\n") as f:
            f.write(content)
        print(f"Wrote: {filepath}")

    # ── Verification ──
    print("\n=== VERIFICATION ===\n")
    all_ok = True
    for filename in FILES:
        filepath = os.path.join(LOC_DIR, filename)

        # 1. File exists
        exists = os.path.isfile(filepath)
        print(f"[{'OK' if exists else 'FAIL'}] {filename} exists")
        if not exists:
            all_ok = False
            continue

        # 2. UTF-8 BOM check
        with open(filepath, "rb") as f:
            raw = f.read()
        has_bom = raw[:3] == b"\xef\xbb\xbf"
        print(f"[{'OK' if has_bom else 'FAIL'}] {filename} has UTF-8 BOM")
        if not has_bom:
            all_ok = False

        # 3. Line count
        text = raw[3:].decode("utf-8") if has_bom else raw.decode("utf-8")
        lines = text.split("\n")
        # Don't count a final empty element from trailing newline
        if lines and lines[-1] == "":
            line_count = len(lines) - 1
        else:
            line_count = len(lines)
        print(f"[INFO] {filename}: {line_count} lines")

        # 4. Single-space indentation (no tabs)
        tab_lines = [i + 1 for i, line in enumerate(lines) if "\t" in line]
        if tab_lines:
            print(f"[FAIL] {filename} contains tabs on lines: {tab_lines[:10]}")
            all_ok = False
        else:
            print(f"[OK]   {filename} uses no tabs")

        # Check that content lines use single-space indent
        bad_indent = []
        for i, line in enumerate(lines):
            stripped = line.lstrip(" ")
            indent = len(line) - len(stripped)
            # Content lines (non-empty, not the header) should use 1-space indent
            if stripped and not stripped.startswith("l_english") and indent > 0:
                if indent != 1:
                    bad_indent.append((i + 1, indent))
        if bad_indent:
            print(f"[FAIL] {filename} has non-single-space indents on lines: {[b[0] for b in bad_indent[:10]]}")
            all_ok = False
        else:
            print(f"[OK]   {filename} all content lines use single-space indent")

        print()

    if all_ok:
        print("ALL CHECKS PASSED ✓")
    else:
        print("SOME CHECKS FAILED ✗")


if __name__ == "__main__":
    main()
