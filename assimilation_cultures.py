from path_constants import mod_path

culture_templates = {
    "anglo": """anglo_[name]= {
    color= rgb{ 200 146 130 }
    religion = protestant
    traits = { anglophone [heritage] }
    
    male_common_first_names = {
        Algernon Alexander Adam Andrew Albert Alphonse Arthur Augustus Anthony Archibald Adolphus Abel Alfred Acton Aylmer Ambrose Austen Adrian Alan Arnold Auberon Allen
        Bruce Benedict Beauchamp Benjamin Byron Bartholomew Barnaby Basil Bertram Bertrand
        Charles Christopher Cecil Chichester Collingwood Cornelius Caleb Clarence Claude
        David Daniel Donald Dudley
        Ebenezer Edward Edmund Edgar Evelyn Egerton Edwin Eustace Eric
        Francis Frederick Frederic Fairfax
        George Gregory Garnet Guildford Gathorne Gerard Gipps Granville Geoffrey Gonville Godfrey
        Harold Henry Hugh Horatio Hedworth Humphrey Harold Harcourt Hedley Herbert
        Isambard Isaac
        John James Jacob Jeremy Joseph Julian Josslyn Joshua
        Kenelm
        Laurence Leonard_2 Lyon Lionel Lewis
        Mark Michael Matthew Massey Montague Myles Murrough Maurice Martin Maxwell
        Nigel Nicholas Nathaniel Neville
        Oliver Octavius Oscar Oswald
        Peter Paul Patrick Poulett Philip Percy
        Richard Robert Roger Rudyard Redvers Rowland Reginald Roundell Rupert Rufus Ross
        Stephen Simon Spencer Stanley Samuel Stafford Sewallis Sackville Sutherland
        Theodore_2 Tristan Theobald Thomas Terence Teignmouth Timothy
        Victor Valentine_2
        Winston Walter William Wilfred Watkin Wellwood Weston Wentworth Wilbraham Wyndham Weetman
        Zachary
    }
    female_common_first_names = {
        Alice Anne Ada Arabella Amelia Adelaide Agnes Alethea Augusta Adela Annot Amabel
        Barbarina Bertha Beatrice Barbara
        Catherine Charlotte Constance Clara Caroline Clementina Cecilia Christabel Camilla Christina
        Dorothea Diana
        Edith Emma Elizabeth Eleanor Eliza Emmeline Esther Euphemia Ella
        Frances Flora Florence Favell Felicia
        Georgia Gertrude Georgiana Geraldine Grace Grisell
        Hannah Harriette Harriet Henrietta
        Isabella Ivy
        Jane Josephine Joanna Julia Jeanette Janet
        Lucy Lydia Louisa Laura Laetitia Lillian
        Mary Marianne Mathilde Margaret May Marian Madeleine Menella Mariana
        Nona Nora
        Olivia
        Phoebe Pauline
        Rachel Rhoda Rosina Rosaline Regina Ruth 
        Sarah Sophia Selina Sibella Susan
        Theodora
        Victoria Violet Virginia
        Wilhelmine
    }
    common_last_names = {
        Allenby Anstruther Abercromby Annesley Assheton Arkwright Acland Armistead Archdale Anderson Akroyd Adair Aytoun Amcotts Allen Amherst Ashton Aytoun
        Brown Buller Barrie Bright Benyon Brinckman Bathurst Bagwell Brewer Bruce Backhouse Bass Bateson Bowring Bourne Barrington Blennerhassett Bourke Beach Beaumont Brassey Bailey Biddulph Brand Baring Baines Brocklehurst Bentall Bazley Birley Bingham Bolckow Baxter Bagge Barttelot Beevor Barbauld Balfour Baillie Barnard Bayly Beerbohm Bellairs Bewick Bloomfield Blagden Borthwick Booth Bousfield Brightwell Broderip Broughton Budden Burdon Borradaile Buxton Beauclerk Bosanquet Bromhead Brightwen Brander
        Cory Chard Courtney Coward Cowell Craufurd Cave Collins Cadogan Chambers Conolly Callan Coleridge Cole Carnegie Cholmeley Clive Croft Cowper Cameron Castlerosse Clay Cogan Colthurst Colebrooke Cross Chaplin Cowen Cartwright Cardwell Corrance Cochrane Conroy Cotton Calthorpe
        Duff Dalrymple Dixon Dalway Dilke Downing Dickson Davison Dalglish Dimsdale Dyott Dowse Dawson Dease Denison Dillwyn Dow Dunnell Despard Day Darter Selkirk
        Edge Ennis Edwards Eaton Elliot Elcho Eastwick Eddowes
        Fortescue Finnie Fordyce Feilden Forster Fowler Fagan Fletcher Fellowes Fothergill Fetherstonhaugh Fanshawe Flowerdew Fullteron Fleming Follows
        Gresley Gooch Grenfell Glass Gilpin Gilbert Grosvenor Goldney Graham Grieve Goschen Gimbert Gardener Grimstead Greenwell
        Howard Hornby Hick Hughes Hardcastle Hope Hibbert Hoare Hodgson Henderson Hanmer Hughes Hutt Holford Holms Hurst Holmesdale Holt Harris Heygate Hodgkinson Headlam Hutton Haig
        Illingworth Ivatt Irby Inchbald Ingelow Inglis
        Jones Johnston Jessel Jardine Jackson Jolliffe
        Kennard Kavanagh Kekewich Keown Knox Kingscote Knightley Kinnaird Kinglake Kempthorne
        Lovelace Laird Lambert Lawson Legh Lennox Lowther Lopes Lefroy Lusk Leatham Lowe Leslie Lane Letby Larwood
        Moore Macfarlane Mellor McClure Muntz Murphy Maguire Matthews Miller Merry Moncreiff Monk Marling Mackintosh McArthur Manners Macfie McLagan Moore McEvoy Mitford McMahon Matheson Moynihan Majendie Mansfield Marindin Markham Maxse McBean McCorrie McDermond McMurdo McWheeney Mouat
        Northcote North Nicol Norwood Nightall Notcott Newdegate Napier
        Otway Ogilvy Onslow Ord Owens
        Primrose Plunket Potter Plimsoll Pakington Pim Pease Playfair Price Pell Pelham Palmer Ponsonby Peppercorn Pennefather Plumptre Pitblado Pardoe Palliser Pardon
        Rawlinson Robertson Ripley Richards Raikes Rebow Round Reed Ramsden Pennington Ross Rumbold Raines Ramage Ridley Rowlands Russell Reddish Ridding
        Stephenson Stanhope Seymour Stronge Sullivan Shaftoe Samuelson Shaw Stapleton Sartoris Saunderson Staveley Strutt Sheridan Stacpoole Scargill Salomons Stansfeld Smith Starkie Synan Seely Shirley Sidebottom Scratchley Sargent Shields Shute Sandbach Sellon Squire Snodgrass Stanger Sibthorp Sparks
        Tite Traill Torrens Tollemache Trehawke Taylor Talbot Tomline Tolman Trevelyan Temple Thornycroft Troubridge Templeton Teesdale Tottenhame Tremayne Titmus Tyldesley
        Upton Underdown
        Veitch Vance Verner Vandeleur Vivian Vicars
        Woollcombe Wedderburn Whitbread Whitmore Willyams Whitworth Waterlow Williamson Wethered Wyllie Wheelhouse Whatman Waterhouse Walsh Winterbotham Weguelin Wedgwood Whitelaw Wheatley Wingate Willan Waugh Wisden
        Young Younghusband
    }
    
    male_noble_first_names = {
        # populate with names here
    }
    female_noble_first_names = {
        # populate with names here
    }    
    noble_last_names = {
        Agar-Ellis Althorp
        Baden-Powell Brudenell-Bruce Bolingbroke Bridport Butler-Henderson Bowes-Lyon Bulwer-Lytton Bertie
        Churchill Cromwell Cavendish Crichton-Stuart Cowell-Stepney Cowper-Temple Crum-Ewing Campbell-Bannerman Cobham Courtenay Caversham
        Dawson-Damer Dalrymple-Hay
        Enfield
        FitzGerald FitzMaurice Ferguson-Davie Falmouth Fane Foley
        Grey Gordon-Lennox Greville-Nugent Graham-Montgomery Goldsmid Green-Price Gathorne-Hardy Glencorse
        Hamilton Haviland-Burke Hill-Trevor Hanbury-Tracy Henley Hampden Hume-Campbell
        Jones-Parry Jervis-White-Jervis
        Keppel
        Loyd-Lindsay Leveson-Gower Launceston Lane
        Maynard Manningham-Buller Meynell-Ingram Montgomery-Cuninghame Mure-Campbell
        Newport Newark 
        Orr-Ewing Ormsby-Gore
        Pleydell-Bouverie Pelham-Clinton Prothero
        Rosebery Ruggles-Brise Ramsay-Gibson-Maitland Rawdon-Hastings
        Salisbury Salusbury-Trelawny Smith-Barry Selwin-Ibeetson Sclater-Booth Somerset Stopford-Sackville Shaw-Lefevre Spencer-Churchill
        Thoroton-Hildyard Torrington Trevor Tadcaster Trematon Townsend
        Walpole Williams-Wynn Wingfield-Baker Wilson-Patten Welby-Gregory Windsor-Clive Wentworth-FitzWilliam Waldegrave Withers-Lancashire
    }
    
    male_regal_first_names = {
        Alexander Albert Augustus
        Edward Edmund
        Frederick
        George
        Henry
        Leopold
        William
    }
    female_regal_first_names = {
        Alexandrina Alice Augusta
        Beatrice
        Elizabeth
        Helena
        Louise
        Margaret Maud Mary
        Sophia
        Victoria
    }
    regal_last_names = {
        Brydges Brudenell-Bruce
        Child_Villiers Conroy
        FitzClarence
        Rawdon-Hastings
        Seymour
    }    
    
    graphics = european
    ethnicities = {
        1 = [ethnicity]
    }
    graphics = [graphics]
}""",
    "franco": """franco_[name]= {
    color= rgb{ 66 108 145 }
    religion = catholic
    traits = { francophone [heritage] }
    
    male_common_first_names = {
        Achille Adolphe Adrien Aimable Alphonse Amedee Antoine Armand Auguste Augustin Alcide Andre Alexandre Athanase Abel Ambroise Aristide AlbE_ric Archambaud Alexis
        Bertrand Bernardin Bernard Barthelemy
        Charles Constant Camille Claude CE_lestin Christophe Cyprien
        Daniel Denis Donat Dominique
        Elie Eugene Edouard E_tienne Emile Emmanuel E_vrard ElzE_ar
        Fernand Francois Frederic Felicien Felix Firmin Ferdinand
        Georges Guillaume Gustave Gaston Guy Germain
        Henri Hippolyte Hubert Hugo Hercule Hugues Hyacinthe
        Jacques Jean Joseph Jules Julien Jeremie JE_rO_me Just
        Lazare Louis Lucien Leopold_2 Leon Laurent Lazare LE_onide LE_once
        Matthieu Michel Marcel Maximilien Maxime Maurice MoI_se
        Napoleon Nicolas
        Olivier Oscar Octave Odilon
        Patrice Paul Philippe Pierre Prosper Pascal
        Quentin
        Robert Roland Rodolphe Raymond RenE_ RE_my
        Sebastien Simon
        Thibaut Thierry Thomas Theophile Theodore ThE_obald
        Ulysse
        Vincent Victor
        Xavier
        Yves
    }
    female_common_first_names = {
        Adelaide_2 Adele_2 Alexandrine Amelie_2 Angelique Anne Antoinette Athenais Augustine
        Beatrice Blanche
        Camille Caroline Catherine Charlotte Claire Clemence Clotilde
        Delphine Diane DesirE_e
        Eleonore_2 Ernestine Eugenie Eulalie
        Francoise
        Gabrielle
        Henriette Hortense
        Jeanne Julie Juliette Justine
        LE_ontine Leopoldine Louise Louise-Victorine
        Marcelle Marguerite Marie Marie-Anne Marie-Felix Marthe Mathilde Melanie
        Pauline Paule
        SE_raphine Sibylle Sophie Stephanie Suzanne
        Therese_2
        Victoire Victorine Virginie
    }    
    noble_last_names = {
        d_Aumont
        Baraguey_d_Hilliers Bergeret de_Beauharnais de_Bussiere de_Broglie de_Boisdeffre
        de_Chastellux de_Chodron_de_Courcel de_CambacE_rE_s de_Croy de_Castelnau de_Cools
        Decazes de_Durfort
        d_Essling
        Fesch
        Gros de_Gramont de_Guerin de_Gueydon de_Goyon
        Kellermann
        Lagrange de_Lamartine de_La_Luzerne de_Leuchtenberg de_Langle_de_Cary
        Marbot de_MacMahon de_Montmorency-Laval Maret de_Morny MassE_na
        de_Noailles Ney_d_Elchingen
        Oudinot
        Pasquier de_Pourtales de_Polignac de_Persigny PalE_ologue
        de_La_Rochefoucauld de_Rochebouet de_Rohan-Chabot
        Suchet de_Sabran de_Saulx de_SE_rent
        de_Talleyrand-PE_rigord
    }
    common_last_names = {
        Anthoine Archinard Augereau Aucouturier Alavoine Achard Astouin Astaix Avond
        Baraguey Bazaine Billot Bosquet Boulanger Bourbaki Boue_de_Lapeyrere Bouet-Willaumez Bugeaud Beaugendre Bronchard Baudet Bodinier Bouillet BiE_re Beslay Bac Bavoux Bezanson Bidard Bonnin Bougueret Boussingault Bouzique Buvignier
        Caillard Canrobert Courbet Cousin-Mountauban de_Castellane Combes ClouE_ Cornet Colas Chauvet Carrere Chartier Combelles Chaude Colin Cruchon Cauvry ChaudE_ Collet Cottrel Charron Caudrelier Courcelles Cibiel Coquerel Coutenceau
        Davout Depre Dubail Dubois Duchene Dupetit-Thouars Desbordes DelcassE_ Dortignacq Dargassies Desgrange Daumain Decaup Dozol Duboc Darche Deloffre Dutiron Denizot Dufour Devilly Dhers Dartigue Degy Delpech Daime Delaire DE_gousE_e Daix Delespaul Debrotonne Demortreux Denissel Desaincthorent Ducluzeau Dudouyt
        Exelmans Emmery Esquirou
        Foch Forey Franchet_d_Esperey Freycinet Faidherbe Fily Fleury Forestier Figuet Farconnet Ferrouillat Foucqueteau Favart Favand Freslon Fresneau
        Gallieni Gouraud Guillaumat de_Gaulle Gain Georget Gabory Guillarme Garrigou Genin GE_raud Godivier Germain Gardent Goujon Gonnor Guyon 
        Hamelin Harispe Hoche Humbert d_Hilliers Habierre Herbelin Harquet
        Jamais Jaures Joffre JaurE_guiberry Jousselin
        Lebouef Lyautey Leygoute Lignon Lallement Lacroix Lafourcade Le_Bars Lachaise Leman Lorillon Lecointe Langlade Leblanc Lagagner Leroy Lapize Lannelongue Lebon Lebelleguy Lubbert Luminais Luneau Lherbette Lortet
        Marmontel Murat de_Montaignac Mazel Maitron ME_nager Meili Mathonat Marrast Madesclaire Malbois Mispoulet Milhoux Moutou
        Niboyet Nivelle Nancy Neboux Nempon Nadaud Nourry Nachet Normant
        Oudin Ory Osmont
        Petain Pellissier Pothier Pasquier Pautrat Payan Passerieu Paulmier Ponson PiE_trois Pardon Paullian Perrenet Pigeon Pleignard Plocq
        Quenon Quinet
        Ringeval Roux Rabot Riviere Roche Riou Ricaux Roquebert Rottie Royannez Radoing Regembal Reibell Repellin Rouher Royol
        Saget de_Saint_Arnaud SouliE_ Sobrier StE_venot Soubigou StoecklE_ Simiot Signard Saint-Beuve Saint-Romme
        Trebutien Trousselier Tuvache Taschereau Tanchard Tassel Teulon Tixier Totain Trinchan
        Vaillant Ventresque Villette Vivier Vaidis Vilette Voilquin Vilain Vignerte Vinoy Valladier Vavin Vendois Vergnes Vernhette Viox
        Wattelier Winant Warnet Walferdin
    }
    male_regal_first_names = {
        Antoine
        Charles
        Ferdinand-Philippe Francois
        Henri
        Louis
    }
    female_regal_first_names = {
        Anne
        ClE_mentine
        Francoise
        HE_lE_ne
        Isabelle
        Louise
        Marie Marie_ThE_rE_se
    }
    regal_last_names = {
        d_Artois
        Bonaparte de_Bourbon de_Bourbon-CondE_
        d_Orleans
    }

    graphics = [graphics]
    ethnicities = {
        1 = [ethnicity]
    }
}""",
    "german": """german_[name]= {
    color= rgb{ 52 67 90 }
    religion = protestant
    traits = { german_speaking [heritage] }
    male_common_first_names = {
        Adelbert Adolf Albrecht Alexander Alfred August
        Bernhard Burkhard Bruno        
        Dieter
        Eduard Edwin Erich Ernst Erwin Esaias
        Florian Franz Friedrich Fritz
        Georg Gustav Gunther Giesebert
        Hasso Heinrich Helmuth Hermann Hugo Haubold Hillart
        Ignatz
        Joachim Johann Jurgen
        Karl Konrad
        Leonhard Leopold Ludwig Lukas
        Manfred Maximilian Markus Michael Moritz
        Nikolaus
        Otto Oskar
        Pascal Paul Peter Philipp
        Reinhard Rudolf Ruprecht
        Stefan
        Theodor
        Wilhelm Wolfgang
    }
    female_common_first_names = {
        Adelheid Armgard Adolphine Albertine Anna Amalie Anna_Dorothea Anna_Sophia Anna_Erika Aurora Agnes
        Beatrix
        Charlotte Cecilia Caroline Christina Clara
        Dorothea_Sophia Dorothea
        Elisabeth Erika
        Friederike 
        Hilda Henriette Hedwig
        Ingeborg
        Julia Johanna
        Luise
        Mathilde Margarethe Maria Marie_Elisabeth Magdalene
        Sigrid Sophie Sophie_Albertine
        Therese
        Viktoria
    }
    noble_last_names = {
        Herwarth_von_Bittenfeld
        Vogel_von_Falkenstein
        von_Falkenstein
        von_Alten von_Anhalt von_Arentschildt von_Arens
        von_Bismarck-Bohlen von_Bittenfeld von_Blomberg von_Blumenthal von_Borries von_Boyen von_Braunschweig von_Breitenbach von_Bulow von_Boyneburg-Lengsfeld von_Breidbach-BUrresheim
        von_Clemm von_Cramm
        von_Doenhoff von_Dieskau
        von_Eck
        von_Fritsch Firnhaber_von_Eberstein
        von_Gebser von_Gagern de_Greiff von_GO_rtz von_GU_nderrode von_der_Gabelentz
        von_Halkett von_Hannover von_Hessen-Darmstadt von_Hessen-Kassel von_Hindenburg von_Hohenzollern von_Holstein-Gottorp von_Hennig von_der_Heydt von_Haupt von_Heyden
        von_Isenburg-BU_dingen-Meerholz
        von_Kleefeld von_Knorr von_dem_Knesebeck
        zur_Lippe
        MU_ller_von_KO_nigswinter von_Manteuffel von_Mecklenburg-Schwerin von_Mecklenburg-Strelitz von_Moltke von_Madai
        von_Niezychowski von_Nordeck_zur_Rabenau
        von_Oldenburg
        von_PlO_nnies
        Riedesel_zu_Eisenbach von_Rauch von_Ravensberg von_Reuter von_Richthofen von_Roon von_Radowitz von_Reichenbach
        von_Sachsen-Altenburg von_Sachsen-Coburg-Gotha von_Sachsen-Meiningen von_Sachsen-Weimar-Eisenach von_Schlieffen von_Schwarzburg von_Spee zu_Stolberg-Wernigerode von_Sybel von_Solms-Laubach von_Stein von_StO_ssert von_Spesshardt
        Treusch_von_Butlar von_Tirpitz von_ThU_nen
        von_Vahlkampf
        von_Waldeck_und_Pyrmont von_Wettin von_Wrangel von_Willich von_Watzdorf Waitz_von_Eschen
        von_Zieten von_Zwierlein
        
        von_Jons
    }    
    common_last_names = {
        Abegg Anger Arendt Ackermann Arntz
        Behncke Boermel Borsig Brill Brommy Blum Baltzer Bever BA_hren Bischoff Brauweiler BrockmU_ller Broix BU_rgers BO_cking Biedermann BlO_de BO_hler Brockhaus Bauer Birnbaum Brunck Buff Bolten Briegleb Bardorf
        Clebsch Cordemann Culemeyer Caspers Cetto Clossett Colonius Compes Carriere Cretzschmar Cratz Cropp
        Dahlmann Dieffenbach Diestel Dreyer Droste Depre Dietze Detering Dietz DuprE_ Dresel
        Ehlert Eichelbaum Eckert Eisenstuck Eissengarthen Elwert Emmerling Ettlinger Erichson
        Feyerabend Fritsch Friedenthal Fabarius Forst Frings Freudentheil Felsing FlU_gge
        Garbe Gerlach Gloger Goerdeler Goetz Grebe Groener Groth Gerlich Giersberg Glaubrech Gail GU_lich
        Hagen Harkort Harych Hassenpflug Heppendorf Hirschfeld Hoffmann Hubatsch Hammer Hecker Herrmann HO_nninghaus Haustein Hensel Henkel Hildebrand Hallwachs Heldmann Hestermann Hesse Hoffmann HU_gel Hollandt
        Jastrow Johow Junghans Jahn Jordan Jungbluth Jungblutte Jucho
        Katz Kempner Kirchweger Koffka Krohn Krummnow Knocke Kehl Keiffenheim Kullich KU_hne Kahlert Kinscherf Kloch Kierulff Kriegk Kugler
        Lasker Leistikow Leonhardt Ludendorff Lehmkuhl Laist Lamberts Landfermann Leue Lingmann Lintz Lederer Lehne Lotheissen Leisler Lang
        Mittwoch Moll Mallmann Marcks Maurer MU_lhens Minckwitz Mohr Manecke Marktscheffel Mappes
        NettstrA_tter Neuerburg Neunzig Nohl
        Olbers Oetker
        Pelz Pax Peiser Plange Pagenstecher Peters Pfeiffer Philippi Prinzen Proff PflU_ger Pitschaft PrA_torius Preusser Pogge Pohle
        Rehfisch Roepke RU_ckert Ronge Reichensperger Reinartz Rittinghausen Ritz Rewitzer Rauschenplat RO_ssler RU_hl Ramspeck Rauschers Reh Runge Reinganum
        Scherfke Schimmelfennig Schmidt Schree Schurz Schnitter SchlO_ffel Stahlschmidt Schwetschke Schnake Schneider Schuchart SchU_renberg Schigard Scheidt Scherer Schleicher SchlO_sser Schmitz SchO_ller Stapper Stedmann Strom Schaffrath SchlU_ter Schnabel Schwarzenberg Steuernagel Stoll Strecker Schleiden Schlettwein Schnelle Stever Sonnenkalb Souchay
        Treibe TU_rke Theyssen Thilmany Trombetta
        Umbscheiden
        Venedy Vogt Volhard Varrentrapp Vorwerck
        Weydemeyer Wittfeld Woehlert Wiesner Wislicenus Wachendorf Waldschmidt Weckbecker Welcker WerlE_ Wesendonck Weilhelmi Winneritz Wirtz Wolfermann Wigard Wuttke Wippermann Wentorp Wendhausen
        Zerrahn ZO_ller Zell Zimmermann ZachariA_ Zulauf Zais
    }

    male_regal_first_names = {
        Adalbert
        Friedrich Friedrich_Wilhelm
        Georg
        Heinrich
        Joachim
        Oskar
        Sigismund
        Wilhelm Waldermar
    }
    female_regal_first_names = {
        Augusta
        Charlotte
        Elisabeth
        Luise
        Margarethe
        Sophie
        Victoria
    }

    graphics = [graphics]
    ethnicities = {
        1 = [ethnicity]
    }
}""",
    "hispano": """hispano_[name]= {
	color= hsv{ 0.06 0.46 0.76 }
	religion = catholic
	traits = { hispanophone [heritage] }
	male_common_first_names = {
		Agustin
		Alberto
		Alejandro
		Alfonso
		Antonio
		Antonio_Maria
		Arsenio
		Augusto
		Baldomero
		Baltasar
		Benito
		Bernardino
		Bernardo
		Calixto
		Carlos
		Celestino
		Claudio
		Cristobal
		Diego
		Dionisio
		Damaso
		Eduardo
		Emilio
		Estanislao
		Federico
		Felipe
		Fernando
		Francisco
		Francisco_Javier
		Felix
		Gabino
		Gabriel
		Gaspar
		Genaro
		Gonzalo
		Ignacio
		Isidro
		Jacobo
		Jaime
		Joaquin
		JosE_
		Jose_Antonio
		Jose_Manuel
		Jose_Maria
		Juan
		Juan_Bautista
		Julio
		Jorge
		Leopoldo
		Lorenzo
		Luis
		Manuel
		Marcelo
		Mariano
		Mateo
		Melchor
		Miguel
		Nicolas_2
		Pablo
		Pascual
		Pedro
		Rafael_2
		Raimundo
		Ramon
		Ricardo
		Santiago
		Sebastian
		Segismundo
		Valeriano
		Vicente
		Alvaro
	}
	female_common_first_names = {
		Adelaida
		Alejandrina
		Amalia
		Antonia
		Bonifacia
		Carlota
		Clotilde
		Concepcion
		Dolores
		Emilia
		Enriqueta
		Eulalia
		Faustina
		Francisca
		Guillermina
		Herminia
		Isabella
		Joaquina
		Manuela
		Maria_2
		Mariana
		Martina
		Robustiana
		Rosa
		Sabina
		Teresa
	}	
	noble_last_names = {
		Alvarez_de_Toledo de_Albornoz de_ArmendA_riz de_Almansa de_AlO_s de_Arteche
		Barrionuevo de_Bohorques de_Bernuy de_Bago
		Cabrera Cagigal_de_la_Vega Colon de_Carvajal del_Carmen_Contreras
		DI_ez_de_Rivera de_Domecq
		Fernandez_de_Cordoba de_la_Fuente Fitz-James_Stuart de_Figueroa Flores_de_SeptiE_n FernA_ndez-Zapata FernA_ndez_de_CO_rdoba
		Garcia_de_la_Noceda GirO_n de_GuzmA_n de_Godoy GonzA_lez_de_Cienfuegos Grimaldi
		Hidalgo_de_Cisneros
		JordA_n_de_UrrI_es
		LO_pez_de_Haro de_Llorach
		MessI_a de_Mercader de_Mora de_Medina del_Milagro_Quesada
		Ortiz_de_la_Riva O_Donnell Osorio_de_Moscoso de_Orozco
		Primo_de_Rivera PE_rez_de_Herrasti de_Palafox PE_rez_de_GuzmA_n PiN_eiro de_Pedro del_Pilar_Osorio
		de_QuirO_s de_Quintanilla
		RamI_rez_de_Saavedra del_Rosario_FalcO_ del_Rosario_Vereterra de_Rojas de_Riquer Ruiz_de_Arana
		SuA_rez_de_ArgudI_n de_Silva de_SatrU_stegui SaI_nz_de_la_Maza de_Samaniego de_Sentmenat de_Salavert de_Santiago_Concha Sanchiz
		de_Tineo
		de_Urquijo de_Uzqueta
		de_Valda del_Valle de_Villalonga de_la_Vera ValdE_s
		de_ZufI_a
	}
	common_last_names = {
		Acuna Aguirre Alcala-Zamora Allendesalazar Alonso Aranda Arguelles-Meres Asensio Aznar Alvarez Acedo Arabolaza Arrate Artola Aranzadi
		Barradas Bugallal BotI_n Bonilla Belaunde Blanco
		Cano Cervera Corsi Cuadrada Comamala
		Diaz_2 DomI_nguez
		Espartero Escoda EguiazA_bal
		Fernandez Franco Fajardo
		Garcia Gonzalez Gil Grasset Galatas
		Heredia Hernandez Herrera Hevia
		Izaguirre
		Linares Lopez Lorenzana Landazabal LarraN_aga
		Maroto Martinez-Campos Maura Menendez Miaja Millan-Astray Mina Mola Munoz Marquez MelE_ndez MedizA_bal Muguerza Moreira Mandiola Muguruza
		Narvaez
		Ortega Otero Onsalo OrdO_N_ez Olaso Ozores
		Pavia Perez PajarO_n Pagaza Pattullo Pena
		Queipo_de_Llano Quintana Quirante
		Rodriguez Rojo Ruiz Reparez Ruete
		Sanjurjo Serrano Silvestre Samitier Serrano Saprissa
		Topete Tuduri Terradas Torralba
		Valdes Varela Villapol Villar Vela Villota Vilalta Vallana VA_zquez
		Weyler
		Yague
		Zamora Zabala
	}
	male_regal_first_names = {
		Alfonso Amadeo
		Carlos
		Felipe Fernando
		JosE_ Juan_Carlos
		Luis
	}
	female_regal_first_names = {
		Beatriz
		Eulalia
		Isabel
		Luisa_Fernanda
		Maria_2 MarI_a_Teresa
	}
	regal_last_names = {
		de_BorbO_n
		de_BorbO_n_Anjou
		de_BorbO_n_Parma
		de_Habsburgo
		de_Orleans
		de_Saboya
		de_Wittelsbach
	}	
	graphics = [graphics]
	ethnicities = {
		1 = [ethnicity]
	}
}""",
    "lusano": """lusano_[name]= {
	color= hsv{ 0.11 0.46 0.76 }
	religion = catholic
	traits = { lusophone [heritage] }
	male_common_first_names = {
		Abel
		Adriano
		Afonso
		Alberto
		Alexandre
		Alfredo
		Andre
		Antonio_2
		Aquilino
		Artur
		Augusto
		Bartolomeu
		Bernardo
		Bruno
		Caetano
		Carlos
		Christovao
		Claudio_2
		Candido
		Damiao
		Daniel
		David
		Dinis
		Diogo
		Duarte
		Ernesto
		Estevao
		Eugenio
		Fernando
		Filipe
		Francisco
		Francisco_Xavier
		Gastao
		Hermenegildo
		Ignacio_2
		Jeronimo
		Joaquim
		Jorge
		JosE_
		JoA_o
		Julio_2
		Leopoldo
		Luis_2
		Manuel
		Miguel
		Mario_2
		Nicolau
		Nuno
		Orlando
		Pascoal
		Paulo
		Pedro
		Rafael_2
		Raul
		Roberto
		Rodrigo
		Rui
		Santiago
		Sebastiao
		Teodoro
		Teofilo
		Tiago
		Tome
		Urbano
		Vasco
		Vicente
		Vitorino
		Vitorio
		Alvaro
		Oscar_2
	}
	female_common_first_names = {
		Adelgundes
		Ana
		Antonia_2
		Avelina
		Benedita
		Bernardina
		Carlota
		Eulalia_2
		Francisca
		Gabriela
		Isabel
		Joana
		Joaquina
		Josefa
		Leopoldina
		Lourcenca
		Maria
		Micaela
		Rafaela
		Rita
		Rosa
		Sofia
		Teresa
	}	
	noble_last_names = {
		Correia_de_Sa
		da_Costa
		da_Cunha
		da_Franca
		da_Silva_Pereira
		de_Albuquerque
		de_Almada
		de_Braganca
		de_Braganca-Coburgo
		de_Carvalho
		de_Caula
		de_Oliveira
		de_Pinho
		de_Queiros
		de_Sousa
		de_Sousa_Coutinho
		de_Vasconcelos
		dos_Anjos
		Rangel
		Rebelo
		Vilela
	}
	common_last_names = {
		Amaral
		Barreto
		Bleck
		Braga
		Cabral
		Capelo
		Carmona
		Coelho
		Correia
		Coutinho
		Dias
		Fernandes
		Ferreira
		Figueira
		Freire_de_Andrade
		Gago
		Gil
		Gomes
		Herculano
		Ivens
		Keil
		Lopes
		Machado
		Magalhaes
		Mendes
		Moniz
		Mouzinho
		Nogueira
		Nunes
		Ortigao
		Pereira
		Pinheiro
		Pinto
		Pires
		Pomar
		Pulido
		Queiroz
		Quintanilha
		Ribeiro
		Rodrigues
		Salazar
		Sampaio
		Silveira
		Sergio_2
		Tavares
		Teixeira
		Vidigal
		Vieira
		da_Silva
		de_Almeida
		de_Arriaga
		de_Castro
		de_Gusmao
		de_Lacerda
		de_Mesquita
		de_Moura
		de_Noronha
		de_Paiva
		dos_Reis
		dos_Santos
	}
	male_regal_first_names = {
		Carlos
		Fernando
		JoA_o JosE_
		Luis_2
		Manuel Miguel
		Pedro
	}
	female_regal_first_names = {
		Adelgundes
		Maria Maria_Ana Maria_Teresa
	}
	graphics = [graphics]
	ethnicities = {
		1 = [ethnicity]
	}
}
""",
    "italo": """italo_[name]= {
    color= hsv{ 0.28 0.17 0.76 }
    religion = catholic
    traits = { italophone [heritage] }
    
    male_common_first_names = {
        Alessandro Alfonso Ambrogio Amedeo Andrea Angelo Antonio Agostino
        Bernardino Bartolomeo Benedetto Bonaventura Bernardo
        Camillo Carlo Cesare Costanzo Casimiro Cristoforo
        Davide Domenico Damiano
        Enrico Enzo Ettore Efisio Emiliano Ernesto
        Fabrizio Faustino Federico Felice Ferdinando Fiorenzo Francesco Filippo Filiberto
        Gaetano Gennaro Girolamo Giulio Giuseppe Guglielmo Giacomo Giorgio Gaspare Gaetano
        Innocenzo Ignazio Ippolito Ilario
        Leopoldo Luigi Luca Lorenzo
        Marco Massimo Matteo Maurizio Massimo
        Nicola
        Oreste Ottavio
        Paolo Pasquale Pietro Prospero
        Raffaele Roberto Ruggiero Romualdo
        Scipione Silvio Simone Serafino Secondo Sebastiano
        Tancredi Tommaso
        Ugo Umberto Urbano
        Vincenzo Vittorio
    }
    female_common_first_names = {
        Beatrice
        Camilla Cassandra Cristina
        Giovannella
        Livia Lucrezia Luisa
        Maddalena Maria Melania Metilde
        Sofia
        Teresa
    }    
    noble_last_names = {
        Avogadro_della_Motta d_Azeglio Annoni_di_Cerro Avogadro_di_Casanova d_Alberti_della_Briga d_Arcais
        Borghese di_Boglio Baldassi Bon_Compagni_di_Mombello Bottone_di_San_Giuseppe Boyl_di_Putifigari Bronzini_Zapelloni De_Benedetti
        Capodilista Carniani Colli_di_Felizzano Colonna di_Calabiana Costa_de_Beauregard Costa_della_Torre De_Castro De_Chambost
        Ferrero_La_Marmora De_Ferrari de_Foresta Falqui_Pes Fecia_di_Cossato
        Gebaix_de_Sonnaz Girod_De_Montfalcon
        d_Ittiri_LedA_
        de_Launay
        Massimo De_Marchi de_Martinel Moffa_di_Lisio_Gribaldi
        Odescalchi Orsini
        Pallavicino Pacoret_de_Saint_Bon Pecori-Giraldi Pellion_di_Persano Pernati_di_Momo Petitti_Bagliani_di_Roreto Ponzo_di_San_Martino
        Ricardi_di_Netro di_Robilant
        Sacchetti di_Savoia di_Savoia-Aosta Solaro_della_Margarita di_Salmour Santa_Croce_Villahermosa Solaroli_di_Briona Somis_di_Chavrie
        Toesca Torelli Thaon_di_Revel
    }
    common_last_names = {
        Acton Albricci Agnes Airenti Amaretti Ara Arminjon Arnulfo Arrifo Asproni Astengo Avigdor Avondo
        Badoglio Baldissera Baratieri Bava-Beccaris Baldassi Benci Baino Barbier BeldI_ Bellono Benintendi Berruti Bersezio Berti Bertini Bertoldi Bezzi Biancheri Bianchetti Bianchi Billiet Blanc Bo Bolmida Bona Borella Botta Bottero Brignone Brofferio Brunati Brunet Brunier Bruschetti Buffa Buraggi Buttini
        Cadorna Cagni Canevaro Capello Caviglia Ceccherini Cialdini Cusani Cabella Caboni Cambieri Campana Canalis Cantara Capriolo Carquet Carta Casaretto Cassinis Castelli Cavalli Cavallini Chenal Chiaves ChiO_ Cobianchi Colli Cornero Correnti Corsi Costa Crosa Cugia
        Dezza Demaria Depretis Durando Daziani Decandia Delfino Delitala
        Emo
        Fanti Fara Filomarino Fara Farina Farini Ferraciu Fescot
        Garibaldi Giardino Govone Gallenga Gallisai Gallo Galvagno Gastinelli Genina Gerbore Germanetti Geymet Ghiglini Gianolio Gilardini Ginet Giovanola Graffigna Grixoni Guglianetti Guillet
        Imperiali Isola
        Lachenal Lanza Louaraz
        Malan La_Marmora Mambretti Menabrea Mozzoni Mameli Mamiani Mantelli Marassi Mari Marongiu Martelli Martin Mathieu Mautino Mazza Melegari Mellana Menabrea Mezzena Michelini Miglietti Miglioretti Minoglio Moia Mongellaz Monticelli Mossi Musso
        Naytana Niccolini Nino Notta
        Orengo Oytana
        Pelloux Perruchetti Pianelli Porro Presbitero Paleocapa Pallavicino Pallieri Pareto Pateri Pescatore Peyrone Pezzani Piacenzi Piane Picinelli Pistone Polleri Polto Porqueddu Pugioni
        Quaglia
        Ramorino Ricotti-Magnani Rattazzi Ravina Rezasco Riccardi Ricci Richetta Robecchi Roberti Rocci Rodini Rossi Rubin
        Sacchi Saletta Sanna Solari Sanguineti Sanna_Denti Sanna_Sanna Sappa Saracco Sauli Scano Scapini Sella Serra Sineo Siotto_Pintor Solari Spano Spinola Sulis
        Tecchio Tegas Tola Torelli Tuveri
        Vaccari Valerio Valvassori Vicari
        Zupelli Zirio
    }
    graphics = [graphics]
    ethnicities = {
        1 = [ethnicity]
    }
}""",
    "slavic": """slavic_[name]= {
    color= hsv{ 0.35 0.40 0.37 }
    religion = orthodox
    traits = { east_slavic [heritage] }
    male_common_first_names = {
        Aleksandr Alexei Andrei Anton
        Boris
        Dmitry
        Fyodor
        Gennady Giorgi Grigoriy
        Igor Ivan
        Kirill Konstantin
        Lavr Leonid Lev
        Maxim Mikhail
        Nikita Nikolai
        Oleg
        Pavel Pyotr
        Roman
        Semyon Sergei
        Valery Vasily Viktor Vladimir Vladislav
        Yegor Yevgeny Yuri
    }
    female_common_first_names = {
        Aleksandra Anastasiya Anna Avdotya
        Daria
        Elena Elizabeta Evgenia Evlalia
        Kira
        Lydia Lyobov
        Maria
        Natalya
        Olga
        Sofia
        Tatiana
        Varvara Vera Yekaterina Yulia
        Xenia
        Zinaida
    }    
    noble_last_names = {
        Adlerberg
        Barclay_de_Tolly Bestuzhev-Ryumin Bulatovich Buturlin
        Dolgorukov Demidov
        Fikelmon
        Greig Gruzinsky Golitsyn
        Ignatiev Ivelich
        Kamensky Kelch Kern Kushelev-Bezborodko Kutaisov Kurakin
        Hoyningen-Huene
        Lopukhin Lobanov-Rostovsky
        Matveyev von_Mohrenheim Meshchersky
        Orlov
        Pistohlkors Putyatin
        Rostopchin Rumyantsev Romanov
        Saltykov
        Tolstoy
        Volkonsky
        Witte
        Yengalychev Yusupov Yuryevsky
    }
    common_last_names = {
        Alexseyev Antonov Azarov
        Badanov Brusilov Budyonny Bolkhovitinov
        Chibisov
        Denikin Dragomirov
        Frolov
        Golovin Grishin Gurko
        Ivanov
        Kasso Kolchak Konev Konstantinov Kornilov Kuropatkin
        Lazarev
        Makarov Menshikov 
        Nakhimov Nebogatov Nikolaevich
        Ostrovsky
        Pavlov Putyatin
        Rozhestvensky
        Shuvalov Skobelev Surkov Sorokin
        Tukhachevsky
        Vorontsov Voroshilov 
        Yegorov Yudenich
        Zavoyko
    }
    male_regal_first_names = {
        Aleksandr Alexei
        Ivan
        Kirill Konstantin
        Mikhail
        Nikolai
        Pavel Pyotr
    }
    female_regal_first_names = {
        Anastasiya Anna
        Elena Elizabeta Evgenia
        Kira
        Maria
        Olga
        Xenia
        Yekaterina
    }
    regal_last_names = {
        Belevsky-Zhukovsky
        Konstantinovich
        Mikhailovich
        Nikolaevich
        Pavlovich Paley
        Romanov
        Vladimirovich
    }

    ethnicities = {
        1 = [ethnicity]
    }
    graphics = [graphics]
}""",
    "hellenic": """hellenic_[name]= {
    color= hsv{ 0.84 0.35 0.38 }
    religion = orthodox
    traits = { greek_culture [heritage] }
    
    male_common_first_names = {
        Alexandros Angelos Anastasios Aristidis Antonios Aristovoulos Alexios Andreas Agamemnon Avgoustos Anthimos Adam Anagnostis 
        Beniamin
        Charilaos Christos Christoforos Christodoulos
        Dimitrios Dionysios Diomidis
        Evangelos Eleftherios Efstathios Emmanouil Epameinontas 
        Filippos Frangiskos
        Georgios Gerasimos Gregorios Germanos
        Ilias Ioannis Iakovos Iraklis Iason
        Konstantinos Kyriakos Kostas
        Leonidas Leon Lambros Lazaros Lykourgos
        Militiadis Menelaos Markos Merkourios Makarios
        Nikos Nikolaos
        Odysseas
        Panos Panagiotis Periklis Petros Pantelis Pantaleon Pavlos Panoutsos 
        Spyridon Sokratis Stamatios Sotiros Stephanos Stelios Stylianos Skarlatos Sofoklis
        Theodoros Tilemachos Thomas Trifon Theodorakis Theophilos Thrasyvoulos Themistoklis
        Vasilios Viktor
        Xenon
        Zacharias
    }
    female_common_first_names = {
        Aikaterini Aganiki Angeliki Asimina Anna Anastasia Alexandra Akrivi Amalia
        Domnitsa Despina Domna
        Evanthia Eliza Elpida Eleni Eleftheria Eirini Evfrosini
        Ilektra
        Kalliroi Kalliopi Konstantina Kiriakoula
        Lena Laskarina Loukia
        Marika Maria Marianna Manto
        Photini
        Sofia Soteria Sevasti
        Thaleia
        Virginia Vassiliki
        Zacharati
    }
    male_regal_first_names = {
        Alexandros
        Filippos
        Georgios
        Ioannis
        Konstantinos
        Nikolaos
        Pavlos
    }
    female_regal_first_names = {
        Alexandra Alexia
        Eleni Eirini
        Konstantina
        Maria
        Olympia Olga
        Sofia
        Theodora
    }

    # some Hellenic forms of names from the "Livre d'Or de la Noblesse Ionienne"
    # also added Souliotes
    noble_last_names = { 
        Arvanitachi Argyropoulos
        Benizelos Botsaris Boutzias Bousbos Boufis Bekas
        Drakos Dousmanis Danglis
        Fotos
        Gonemis Galatis
        Iras
        Kolokotronis Kapodistrias Kalogeras Kallergis Kartanos Koutsonikas Kaskaris
        Levidis Landos
        Metaxas Manos Mavromichalis Mavrokordatos Mamonas Marmoras Mantzos Matis Mourouzis
        Notaras Nikas Negreponte
        Pieros Polylas Prosalendi Patrikios Papagiannis Palamas Pandazis
        Rodostamos Rallis
        Soutsos Seos Sachinis Salataris
        Theotokis Tzavelas Thanasis Toras Todis Tzoris
        Vlassopoulos Velios Vasos
        Ypsilantis
        Zarbas
    }
    common_last_names = {
        Andreou Aspiotis Andriakopoulos Athanasopoulos Anninos Athanasiou Akratopoulos Antonpoulos Asimakopoulos Axiotis
        Belokas Benardis Baltatzis
        Chalkokondylis Chrysafis Chorafas Chrysafos Chazapis Charalambis
        Deligiannis Damaskos Diamantis Diamantopoulos Dontis Drivas Dalezios Douros
        Eftaxias
        Fetsis Fetsios Frangoudis Frangopoulos Foustanos Farmakidis Freris Farmakidis Fotilas
        Gennimatas Golemis Gerakeris Grigoriou Gouskos Georgiadis Gaitanos Grigoriadis Gneftos Gazis
        Hatzidakis
        Iatrou Iatridis 
        Karousou Karakatsanis Kafetzis Koletis Kostantinidis Konstantinou Karakalos Karvelas Karagiannopoulos Karasevdas Karagiannis Katravas Khatzis Kontos Koukoudakis Kourkoulas Kasdaglis Kallisperi Kanaris Konstantas
        Lagoudakis Lavrentis Loverdos Loundras Langakis Levidis Lamprakis Laskaridis Lerias Liapis Logothetis
        Merkatis Mouratis Masouris Mitropoulos Mikhailidis Moustakopoulos Morakis Mangourakis Markou Marnezos Mazoukas Mikhalopoulos Malokinis Mavrommatis Mavrogenes Mansolas
        Nikolopoulos Nastos Neroutsos Negris
        Orphanidis Orlandos
        Paraskevopoulos Papasymeon Papadiamantopoulos Persakis Papasideris Pierrakos-Mavromichalis Poulos Pyrgos Petmezas Papaioannou Pavlidis Platis Petrou Pantazidis Patsouris Pothitos Pepanos Paspatis Petrokokkinos Papafingos Peppas Psychas Printezis Papailiopoulos
        Romantzas Rallis Roussos
        Skaltsogiannis Stais Sanidis Salouros Santanis Stournaras Siganous Skandalidis
        Theodoropoulos Tryfiatis-Tripiaris Tsiklitiras Theofilakis Trikoupis Triantafyllakos Tombazis
        Versis Vasilakos Vrettos Vouros Vourakis Vavis Valetsiotis Vlachos Vikhos Vrasivanopoulos Vlassis Vourvoulis Voustinos Vakondios Varthalitis
        Xydras Xenakis Xenopoulos Xylinakos
        Zoumis Zanos Zacharopoulos Zervinis Zafyropoulos Zarifi
    }

    ethnicities = {
        1 = [ethnicity]
    }
    graphics = [graphics]
}""",
    "arab": """arab_[name]= {
    color= rgb{ 144 154 79 }
    religion = sunni
    traits = { arab_speaking [heritage] }
    male_common_first_names = {
        Abd_Allah
        Abd_al-Karim
        Abd_al-Malik
        Abd_al-Qadir
        Abd_al-Rahman
        Abu_Bakr
        Ahmad
        Ali
        Fawzi
        Fuad
        Halil
        Hasan
        Hisham
        Ibrahim
        Ishaq
        Iskandar
        Ja_far
        Jamal
        Kamil
        Khalid
        Muhammad
        Mustafa
        Nur_al-Din
        Sa_d_al-Din
        Sa_ud
        Salim
        Shukri
        Tawfiq
        Umar
        Uthman
        Yahya
        Yusuf
        Zafir
    }
    female_common_first_names = {
        Bahiya
        Fahda
        Ghaliyya
        Haifa
        Hamida
        Hassa
        Iffat
        Latifa
        Lolwah
        Maha
        Noura
        Sultana
    }    
    noble_last_names = {
        al_Hashimi
        Al_Maktoum
        Al_Mualla
        al_Nuaimi
        al_Qasimi
        al_Rashid
        al_Saud
        Al_Sharqi
        al_Ulayyan
    }
    common_last_names = {
        al-Hijazi
        al-Najdi
        ibm_Kamil
        ibn_Abd_Allah
        ibn_Abd_al-Qadir
        ibn_Abu_Bakr
        ibn_Ahmad
        ibn_Ali
        ibn_Fuad
        ibn_Halil
        ibn_Hasan
        ibn_Hisham
        ibn_Ishaq
        ibn_Ja_far
        ibn_Khalid
        ibn_Muhammad
        ibn_Mustafa
        ibn_Salim
        ibn_Umar
        ibn_Uthman
        ibn_Yusuf
    }
    ethnicities = {
        1 = [ethnicity]
    }
    graphics = [graphics]
}""",
    "sino": """sino_[name]= {
    color= rgb{ 190 80 48 }
    religion = confucian
    traits = { sinosphere [heritage] }
    male_common_first_names = {
        Chen
        Cheng
        Deng
        Dong
        Gao
        Hsia
        Hu
        Huang
        Kong
        Kwong
        Li
        Liang
        Liao
        Liu
        Luo
        Ma
        Mao
        Pan
        Tan
        Wang
        Xie
        Yang
        Yu
        Zhang
        Zhu
    }
    female_common_first_names = {
        Akew
        Jin
        Jinhong
        Junying
        Qingtang
        Sanniang
        Shanziang
        Shih
        Taiqing
        Xiefen
        Xiugu
        Xuanjiao
        Yu
        Yunmei
    }    
    noble_last_names = {
        Cui
        Li
        Nie
        Zhang
    }
    common_last_names = {
        Dong
        Fang
        Hu
        Jiang
        Jin
        Lu
        Ma
        Peng
        Qiu
        Shen
        Sun
        Tian
        Ting
        Wei
        Wu
        Ye
        Zhao
    }
    ethnicities = {
        1 = [ethnicity]
    }
    graphics = [graphics]
}""",
    "iranian": """iranian_[name]= {
    color= hsv{ 0.0 0.33 0.46 }
	religion = shiite
	traits = { iranian_turanian_culture_group [heritage] }
	male_common_first_names = {
		Abbas Abdolazim Abdolhossein Abdolsamad Abolghasem Ahmad Ali 
		Bahram 
		Ebrahim Esmail 
		Fath_Ali Fazlollah
		Hamzeh Hasan Hossein
		Kamran Karim
		Lotf_Ali
		Mahmoud Massoud Mohammad Moin_ed-Din Mozzafer_ed-Din Muhsin Murad
		Naser_ed-Din Nosret
		Reza
		Sadegh
	}
	female_common_first_names = {
		Asieh
		Bibi_Khatoom
		Ghazaleh
		Marjane Marsha Maryam
		Sedigheh
	}	
	noble_last_names = {
		al-Saltaneh Alamir Astarabadi Ashtiani
		Bakhtiari
		Farmanfarma
		Hakimi Hedayat
		Khalatbari 
		Pirnia
		Qajar
	}
	common_last_names = {
		Airom Ansari Ayrum
		Buzarjomehri
		Davallu
		Esfahani
		Farhani
		Jahanbani Jamshidian
		Kashani Khan Khuzai
		Meshhedi
		Nakhchevani
		Pesyan
		Rokni
		Sadegh Shafaei Shahbakhti Shirazi
		Tabrizi Tahmasebi
		Zahedi
	}
	male_regal_first_names = {
		Ahmad
		Fath_Ali Fereydoun
		Mahmoud Mohammad Mohammad_Ali Mohammad_Hassan Mozzafer_ed-Din
		Naser_ed-Din
		Sultan_Hamid
	}
	ethnicities = {
		1 = [ethnicity]
	}
	graphics = [graphics]
}""",
    "dutch": """dutch_[name]= {
	color= hsv{ 0.07 0.49 0.83 }
	religion = protestant
	traits = { beneluxian_culture_group [heritage] }
	male_common_first_names = {
		Abraham
		Adolf
		Adriaan
		Alexander
		Andreas
		Andries
		Antonius
		Antoon
		Barthout
		Casimir
		Christiaan
		Christoffel
		Constantijn
		Cornelis
		Daniel
		Daniel_2
		David
		Dirk
		Dominicus
		Drikus
		Eduardus
		Eise
		Elias
		Ernst
		Erwin
		Frans
		Frederik
		Gabriel
		Gaspar
		Gerard
		Gerben
		Gijsbert
		Godfried
		Gustaaf
		Hans
		Hendrik
		Hugo
		Isaac
		Jacob
		Jan
		Jeroen
		Johan
		Joost
		Jurgen_2
		Karel
		Kasper
		Laurens
		Lodewijk
		Luuk
		Marius
		Matthijs
		Maurits
		Maximiliaan
		Merkus
		Moritz
		Nikolaas
		Paul
		Pauwel
		Pieter
		Quinten
		Rafael
		Richardus
		Roeland
		Rogier
		Ruben
		Rudolf
		Rutger
		Simon
		Stefan
		Thomas
		Victor
		Vincent
		Willem
		Zacharias
	}
	female_common_first_names = {
		Aletta Annewies Anna Anna_Louisa
		Beatrix
		Cornelie Christina Catharina Constantia
		Diderika
		Emma Eufemia
		Felicia
		Goverdine
		Henrieette
		Ida
		Juliana Johanna Jacoba
		Louise Lessina
		Maria Martha Margaretha
		Pauline Petronella
		Roosje 
		Suzanna Sjoukje Sara
		Wilhelmina
	}	
	noble_last_names = {
		van_Boetzelaer
		van_Coeverden
		van_Doorn
		De_Geer
		Lampsins van_Lynden van_Lyere
		van_den_Velden de_Vos_van_Steenwijk
		van_Egmont
		van_Saksen-Weimar
		van_Oranje-Nassau
		Schimmelpenninck_van_der_Oye
		Melvill_van_Carnbee
		van_Wassenaer
	}
	common_last_names = {
		Batenburg
		Bentinck
		Boetge
		Boreel
		Boumeester
		Brandt
		Brouwer
		Buyskes
		Broekhof
		Uiterwijk
		Chasse
		Cleerens
		Cochius
		Coehoorn
		Coen
		Coops
		Cort-Heyligers
		Crijnssen
		Daendels
		Deijkerhoff
		Duycker
		Ellis
		Engels
		Engelvaart
		Evertzen
		Fabius
		Gregory
		Janssens
		Kater
		Kool
		Kortenaer
		Kruys
		Kohler
		Kuiper
		List
		Lucas
		Martena
		Michiels
		Nachtegaal
		Nahuys
		Nepveu
		Ongerboer
		Reijersen
		Rijk
		Roell
		Sabron
		Schenk
		Schouten
		Spiegel
		Staal
		Steltman
		Stokhuyzen
		Stuyvesant
		Tasman
		Trip
		Van_Utenhove
		Verspijck
		Vetter
		Weitzel
		Wolterbeek
		de_Casembroot
		de_Constant_Rebecque
		de_Eerens
		de_Grouwe
		de_Houtman
		de_Kock
		de_Moor
		de_Rijk
		de_Winter
		den_Beer_Poortugael
		van_Assendelft
		van_Braam_Houckgeest
		van_Brederode
		van_Bronkhorst
		van_Culemborg
		van_Dambenoy
		van_Diemen
		van_Duivenvoorde
		van_Galen
		van_Geen
		van_Ham
		van_Haren
		van_Heemskerck
		van_Heutsz
		van_Hoensbroeck
		van_Huchtenbroek
		van_Ilpendam
		van_Keppel
		van_Marnix
		van_Nieuwenaar
		van_Noort
		van_Pallandt
		van_Raephorst
		van_Rechteren
		van_Renesse
		van_Riebeeck
		van_Rossum
		van_Spilbergen
		van_Swieten
		van_Troyen
		van_Vredenburch
		van_Walbeeck
		van_Wesembeke
		van_Wijngaarden
		van_Wingle
		van_den_Bosch
		van_der_Aa
		van_der_Capellen
		van_der_Does
		van_der_Heijden
		van_der_Werff
		van_der_Wijck
	}
	male_regal_first_names = {
		Alexander
		Ernst_Casimir
		Frederik_Hendrik
		Hendrik
		Maurits
		Willem Willem_Alexander Willem_Frederik
	}
	female_regal_first_names = {
		Alexia Ariane
		Beatrix
		Catharina_Amalia Christina
		Irene
		Juliana
		Margriet
		Sophie
		Wilhelmina
	}
	graphics = [graphics]
	ethnicities = {
		1 = [ethnicity]
	}
}""",
    "japanese": """japanese_[name]= {
    color= hsv{ 0 0 90 }
    religion = mahayana
    traits = { yamato [heritage] }
    male_common_first_names = {
        Aritomo Gentaro Gonnohyoe Goro Hayao Heihachiro Hikonojo Hiroshi Hyoe Iwao Jinzaburo Jiro Kageaki Kagenori Kantaro Kazushige Keisuke Kenkichi Kiyotaka Koichiro Kotohito Kozo Kuranosuke Maresuke Masatake Masujiro Michisura Mineo Mitsue Mitsuomi Nariaki Nobuyoshi Rokuro Sadao Samata Shichiro Shigeru Shigeto Shinsaku Shoin Soroku Sotokichi Sukenori Sukeyuki Sumiyoshi Tadakuni Takamori Takayoshi Takeaki Tamemoto Taro Taruhito Tetsutaro Tomasaburo Tomonosuke Toshimichi Toshiyoshi Tsugumichi Yahachi Yasukata Yasuyoshi Yoshida Yoshifuru Yoshika Yoshimichi Yoshinobu Yoshinori Yusaku
    }
    female_common_first_names = {
        Asako Chikako Ginko Gyokuran Kaho Kei Kin Kumehachi Masako Miki Natsu Nobu Oi Rengetsu Sayoko Teru Toyoko Tsuneko
    }
    noble_last_names = {
        Hayashi Ito Jutoku Kujo Matsudaira Mitsune Nabeshima Togo Tokugawa
    }
    common_last_names = {
        Akiyama Araki Arichi Arisugawa Dewa Enomoto Hasegawa Honjo Ichinohe Inoue Itagaki Kabayama Kamimura Kamio Kanin Kataoka Kato Katsu Katsura Kawakami Kawamura Kido Kodama Kuroda Kuroki Makino Masaki Minami Muto Nakamuta Nire Nogi Nozu Okada Oku Okubo Omura Osumi Oyama Saigo Sakura Sato Shibayama Shimamura Shirakawa Suzuki Tachibana Takashima Takasugi Tamon Terauchi Tsuboi Ueda Uehara Ugaki Uryu Yamagata Yamakawa Yamamoto Yamashita Yamaya Yashiro Yui
    }
    graphics = [graphics]
    ethnicities = {
        1 = [ethnicity]
    }
}""",
    "indo_aryan": """indo_aryan_[name]= {
    color= hsv{ 0.12 0.70 0.60 }
    religion = hindu
    traits = { indo_aryan_language [heritage] }
    male_common_first_names = {
        Aakash Amratlal Ashoka Balwantry Chandrakirti Chandraka Dhalip Ganda Govind Harishankar Ishvari Jassa Kapur Lokendra Madhukar Nau Nihal Pheran Purnananda Raghuraj Ranjit Shivshankar Udit Veer
    }
    female_common_first_names = {
        Alka Amrita Anuradha Asha Bhawana Datar Ganga Hema Indira Jind Mehtab Nidhi Priyanka Rani Sada Sampat Savita Uma
    }
    noble_last_names = {
        Arkvanshi Bahadur Bajpai Bhangi Chauhan Deva Jaitely Kunwar Nehru Phulkian Prasad Shah Singh
    }
    common_last_names = {
        Ahluwalia Ambani Bharti Bhave Biswas Das Devi Dhillon Gandhi Gupta Janak Joshi Kaur Kunwar Mishra Nayar Phukan Ram Sastri Sharma Shukla Singh Tiwana Verma Yadav
    }
    graphics = [graphics]
    ethnicities = {
        1 = [ethnicity]
    }
}""",
    "dravidian": """dravidian_[name]= {
    color= hsv{ 0.94 0.57 0.70 }
    religion = hindu
    traits = { dravidian [heritage] }
    male_common_first_names = {
        Alluri Basaveshwara Chidambaram Durgabai Harihara Kandukuri Kempe Krishnadeva Narasimha Pingali Potti Raja Rajagopalachari Ramaswami Seshayya Shanmukham Subramania Tanguturi Uyyalawada
    }
    female_common_first_names = {
        Anjali Aparna Chindodi Fathima Lakshmi Manjula Nageswari Rajini Rani Saraswati Sudhamani
    }
    noble_last_names = {
        Bahadur Hegde Iyer Menon Nayak Narayan Rajagopalachari Rao Raya Salarjung Sethupathi Tondaiman
    }
    common_last_names = {
        Ballala Bibi Deshmukh Gowda Hanumathu Kattabomman Kesavadas Krishnamachari Mudaliar Naidu Nayudu Perumal Pillai Sitaramaraju Sriramulu Veeresalingam Wodeyar
    }
    graphics = [graphics]
    ethnicities = {
        1 = [ethnicity]
    }
}""",
    "bantu": """bantu_[name]= {
    color= hsv{ 0.15 0.65 0.45 }
    religion = animist
    traits = { bantu [heritage] }
    male_common_first_names = {
        Agyeman Amadi Atakora Bakari Chane Chionesu Dume Gamba Githinji Ilunga Jideofor Juma Kabili Kasongo Kofi Kwame Mburumba Mensa Mzilikazi Ngengi Onsei Orji Owusu Sekayi Shaka Tichawonna Wamwara Zuka
    }
    female_common_first_names = {
        Abisagi Akousua Ambwene Chima Danai Fulu Kakenya Mmanthatisi Nandi Nwanyieze Serwaa_Nyarko Thandi Wambui Yaa_Akyaa
    }
    noble_last_names = {
        Asante Banda Buthelezei Denkyira Ilunga kaJama Kambazembi Keita Maharero Moshoeshoe Nnofo Nri Rozwi
    }
    common_last_names = {
        Achebe Akengbedo Bonsu Cilemo Dacche Deng Fofie Gqunu Hanga Kalombo Kony Kuai Kwenda Lobengula Maina Mtemi Ngwale Njovu Nyamazana Onyeso Phiri Prempeh Soshangane Tene wa_Ngengi
    }
    graphics = [graphics]
    ethnicities = {
        1 = [ethnicity]
    }
}""",
    "turkic": """turkic_[name]= {
    color= hsv{ 0.99 0.48 0.80 }
    religion = sunni
    traits = { turkic [heritage] }
    male_common_first_names = {
        Abdulhamid Abdullah Ahmet Ali Alimqul Arif Aslan Bahaeddin Bekir Cemal Enver Fahri Fevzi Fuat Halil Hasan Haydar Heydar Ibrahim Ismet Izzet Kazim Kemal Mahmud Mehmed Murad Musa Mustafa Namik Numan Nurettin Omar Osman Rauf Reshad Selim Suleyman Talat Yaqub Yusuf Ziya
    }
    female_common_first_names = {
        Aisha Alaviyya Ayse Aziza Emina Fatma Gulimina Gulnazar Hamida Maryam Nasiba Sakina Samal
    }
    noble_last_names = {
        Ankuap Arpazli Ashurbeyov Balyan Bayero Beg Benderli Cengic Dantata Karaosmanoglu Khan Koprulu Osmanoglu Saraki Shah
    }
    common_last_names = {
        Abdulbaqi Akbas al-Kanemi Aytakov Bahadur Bakikhanov Bayramov Burhan Eczacibashi Hasagasi Ildyrym Koc Kosalay Masanchi Mehmandarov Mulos Oezal Rasulzade Sabanci Taymur Zardabi
    }
    graphics = [graphics]
    ethnicities = {
        1 = [ethnicity]
    }
}""",
    "malay": """malay_[name]= {
    color= hsv{ 0.92 0.49 0.60 }
    religion = sunni
    traits = { malay_culture [heritage] }
    male_common_first_names = {
        Abul Abdurrahman Ahmad Amir Anom Arifin Bambang Daud Emilio Hasyim Jose Juan Kiras Manuel Muhammad Panembahan Slamet Soekarno Ton_That Tran Truong
    }
    female_common_first_names = {
        Atiqah Brijida Carmen Catalina Fatin Leona Lien Mai Maria Megawati Sari Siti Sunarti Tatiek
    }
    noble_last_names = {
        Aguainaldo al_Qadri Bonifacio Bukitan Djajadiningrat Hamengkubuwono Le Manisia Marga_Sinambela Ngo_Dinh Pakualaman Sastrowardoyo
    }
    common_last_names = {
        Akbaruddin Angkat Arellano Bangun Bintang Buu_Lan Capah Cirebon Cuong del_Pilar Diwa Gajah Han Juhah Kaloko Khairuddin Meka Mien_Lam Pasi Rizal Salihin Sinamo
    }
    graphics = [graphics]
    ethnicities = {
        1 = [ethnicity]
    }
}""",
    "north_american": """north_american_[name]= {
    color= hsv{ 0.63 0.30 0.52 }
    religion = animist
    traits = { north_american_group [heritage] }
    male_common_first_names = {
        Apuckshunubbee Barboncito Billy Catecahassa Cheeseekau Cochise Gabriel Geronimo Guyasuta Hehaka Henry_Chee Husishusis_Kute Inkpaduta John Joseph Kaintwakon Lalawethika Louis Manuelito Ollokot Peter Quanah Skenandoa Tamaha Tenskatawa Toohoolhoolzote Wanata
    }
    female_common_first_names = {
        Alliquippa Azayamankawin Chipeta Dehhewanis Gahonnoneh Kaniehtiio Marie-Anne Methoataske Naduah Nonhelema Owanah Polly Rosalie Sacagawea
    }
    noble_last_names = {
        Abeel Ahenakew Blacksnake Boudinot Bowlegs Brant Cornplanter Dodge Hastiin_Dagha Kahkewistahaw Lathlin Lepine McIntosh Riel Ridge Ross Sayer Vann
    }
    common_last_names = {
        Ahtahkakoop Anderson Bissette Bruce Buck Buffalo Bull Calf Child Crane Decoteau Dumont Folsom Harjo Hicks Huste Iyotake Jemison Lacerte Lesperance Logan Martin McQueen Montour Parker Pitchlynn Powell Rain Sapa Tecumseh Vandal Witko
    }
    graphics = [graphics]
    ethnicities = {
        1 = [ethnicity]
    }
}""",
    "mesoamerican": """mesoamerican_[name]= {
    color= hsv{ 0.47 0.29 0.38 }
    religion = catholic
    traits = { native_mesoamerican_culture_group [heritage] }
    male_common_first_names = {
        Agustin Akbal Andres Antonio Benito Carlos Cristobal Cuautehmoc Diego Emiliano Felipe Gaspar Hernando Jacinto Jesus JosE_ Juan Luis Manuel Martin Miguel Porfirio Santiago Yumil
    }
    female_common_first_names = {
        Ana Antonia Amaranta Celsa Cleofas Cristina Delfina Eufrosina Eva Felipa Jovita Laureana Lina Maria Matilde Ramona Rosalina Sofia
    }
    noble_last_names = {
        Altamirano Ay Calderon Ceel Chan Charis Chi Cortes Henestrosa Juarez Pat Pec Poot Tamayo
    }
    common_last_names = {
        Ak_ab_al Almonte Atlanteco Badiano Cal Canek Canul Carrillo Ceh Chinas Coc Coyotl Cristobal Cuautlaxahue Fernandez Garcia Gonzalez Gutierrez Huanitzin Ixtlilxochitl Jimenez Lopez Matus Menchu Morales Ortiz Pineda Pop Puk Ruiz Tecu Valeriano Xochitl Zapata
    }
    graphics = [graphics]
    ethnicities = {
        1 = [ethnicity]
    }
}""",
    "south_american": """south_american_[name]= {
    color= hsv{ 0.10 0.22 0.69 }
    religion = catholic
    traits = { south_american_group [heritage] }
    male_common_first_names = {
        Agustin Alejandro Antonio Anibal Aucan Bartolome Carlos David Diego Evo Felipe Francisco Gregorio Hugo Jacinto JosE_ Juan Luis Manuel Martin Maximo Pablo Pedro Ramon Roque Santiago Simon Tupac Victor
    }
    female_common_first_names = {
        Adela Angelica Bartolina Carola Celsa Claudia Eliza Emilia Janequeo Juana Maria Mercedes Micael Modesta Sara Silvia Veronica
    }
    noble_last_names = {
        Anzoategui Apaza Calfucura Colipi Collahuazo Conoepan Cusicanqui Katari Melin Namuncura Poma Quispe Santa_Cruz Sisa Tiaraju Tumpa Vargas
    }
    common_last_names = {
        Alvarez Arguedas Ayme Barrientos Calfucur Calisaya Camba Cardenas Chambi Choquehuanca Condori Diaz Fernandez Gonzalez Guaman Gutierrez Hernandez Huallpa Humala Lopez Mamani Morales Ortiz Paredes Patino Puma Riquelme Rodriguez Sosa Toledo Torres Velazquez
    }
    graphics = [graphics]
    ethnicities = {
        1 = [ethnicity]
    }
}""",
    "west_slavic": """west_slavic_[name]= {
    color= hsv{ 0.66 0.32 0.99 }
    religion = catholic
    traits = { west_slavic [heritage] }
    male_common_first_names = {
        Adam Aleksander Alois Andrej Antonin Bedrich Boleslaw Bronislaw Edvard Emil Eustachy Frantisek Gustav Henryk Ignacy Jakub Jan Jaroslav Jiri Jozef Karol Kazimierz Ladislav Leopold Ludwik Maciej Marian Michal Mikulas Pavel Peter Roman Stanislaw Stefan Tadeusz Vaclav Vojtech Zygmunt
    }
    female_common_first_names = {
        Anna Barbara Blanka Elena Emilia Ewelina Helena Irena Ivana Jaroslava Karolina Katerina Klara Ludmila Maria Olga Stefania Tereza Ursula Zofia Zuzana
    }
    noble_last_names = {
        Bernolak Bor-Komorowski Clary_Aldringen Colloredo-Mansfeld CzetwertyN_ski Daxner Glowacki GoL_uchowski Harrach Jesensky Kollar Lichnovsky L_ubieN_ski OgiN_ski Pilsudski Potocki Radziwill Sapieha Thun-Hohenstein z_Lobkovic
    }
    common_last_names = {
        Balaban Basch Benes Blaho Brzoska Celovsky Chlapowski Dabrowski Dvorak Fibich Gajda Hlinka Hodza Jirecek Kafka Kollar Kucera Langiewicz Masaryk Moravec Nemecek Neruda Nowak Novotny Ostrowski Popper Radecky Safarik Smetana Sowinski Stefanik Svoboda Tiso Traugutt Weber
    }
    graphics = [graphics]
    ethnicities = {
        1 = [ethnicity]
    }
}""",
    "south_slavic": """south_slavic_[name]= {
    color= hsv{ 0.97 0.26 0.58 }
    religion = orthodox
    traits = { jugoslav [heritage] }
    male_common_first_names = {
        Alaksandar Andrija Antun Blagoje Bozidar Branko Danilo Dragutin Dusan Franjo Ivan Janko Josip Juraj Karlo Kresimir Ljudevit Milan Milos Mirko Miroslav Nikola Pavle Petar Radomir Slavko Stjepan Tomislav Vladimir Vojislav Zivojin
    }
    female_common_first_names = {
        Aleksandra Ana Anka Darinka Draga Dragojla Ivana Jelena Katarina Marija Milena Natalia Ruza Tereza
    }
    noble_last_names = {
        Anastasijevic Avakumovic Draskovic Garasanin Gradi Izetbegovic Jelacic Karadordevic Kukuljevic Mazuranic Nenadovic Obrenovic Pejacevic Pozderac Sarkotic Zrinski
    }
    common_last_names = {
        Alapic Bakaric Belimarkovic Bilic Blazevic Boroevic Brankovic Cuvaj Dapcevic Frankopan Gaj Getaldic Gundulic Hadzilic Horvatovic Imamovic Jankovic Jovanovic Kulenovic Lesjanin Maric Mihailovic Misic Nazor Nedic Novak Panic Pesic Petrovic Popovic Putnik Pucic Selimovic Sokolovic Stepanovic Tomasic Vukotic Zivkovic
    }
    graphics = [graphics]
    ethnicities = {
        1 = [ethnicity]
    }
}""",
    "celtic": """celtic_[name]= {
    color= hsv{ 0.35 0.58 0.54 }
    religion = catholic
    traits = { celtic_people [heritage] }
    male_common_first_names = {
        Alexander Arthur Brian Cathal Christopher Con Daniel Denis Desmond Edward Eamon Fionan Frank George Harry Jack James John Joseph Kevin Liam Michael Murrough Patrick Peter Richard Robert Sean Thomas William
    }
    female_common_first_names = {
        Adela Anne Bithia Bridget Catherine Charlotte Clotilde Edith Ellen Emily Gertrude Honora Ida Isobel Jane Josephine Laura Letitia Louisa Margaret Mary Nora Olivia Rose Sarah Sophie
    }
    noble_last_names = {
        Beresford Browne Castlereagh Conyngham FitzGerald FitzMaurice Glenavy Hamilton Hill Lambart Loftus Mornington O_Brien Plunket Talbot Taylor Vane-Tempest
    }
    common_last_names = {
        Aiken Ashe Boyle Brady Breen Brennan Brown Brugha Burke Byrne Campbell Carroll Clarke Collins Connolly Connor Cosgrave Craig Daly Doherty Donnelly Doyle Duffy Dunne Farrell Fitzpatrick Flynn Gallagher Griffith Hayes Healy Hughes Johnston Kelly Kennedy Larkin Lynch Maguire Mallin Martin McCarthy Moore Moran Mulcahy Murphy Murray Nolan O_Connor O_Higgins O_Leary Pearse Power Quinn Reilly Ryan Smith Sullivan Walsh White Wilson
    }
    graphics = [graphics]
    ethnicities = {
        1 = [ethnicity]
    }
}""",
    "hungarian": """hungarian_[name]= {
    color= hsv{ 0.25 0.22 0.99 }
    religion = catholic
    traits = { hungarian_culture_group [heritage] }
    male_common_first_names = {
        Alajos Albert Andras Aurel Benedek Bertalan Bela Daniel_3 David_2 Erno Ferencz Gyula Gyorgy Gabor Ignac Imre Istvan Janos Jozsef Kalman Karoly Lajos Laszlo Mihaly Mor Sandor Peter_2 Vilmos Zsigmond
    }
    female_common_first_names = {
        Amalia_2 Anna Bertha Brigitta Emilia Emma Flora Fruzina Judit Katalin Kornelia Maria Nina Rozalia Terez Vilma Zsuzsanna
    }
    noble_last_names = {
        Andrassy Deak Erenyi_Ullmann Frakashazi_Fischer Laczkovics Lahner Leiningen-Westerburg Lichtenstein Osterreicher von_Benedek Zrinyi
    }
    common_last_names = {
        Apponyi Aulich Baross Batthyany Beothy Bothmer Damjanich Dessewffy Egressy Farkas Goldziher Gungl Hauszmann Heller Horthy Jaszai Joseffy Katona Kaufman Kiss Knezich Lazar Liszt Mikszath Molnar Nagy-Sandor Ottinger Perczel Poeltenberg Remenyi Rohr Schweidel Szemere Szechenyi Tersztyansky Torok Varga Vecsey
    }
    graphics = [graphics]
    ethnicities = {
        1 = [ethnicity]
    }
}""",
    "scandinavian": """scandinavian_[name]= {
    color= hsv{ 0.64 0.57 0.62 }
    religion = protestant
    traits = { scandinavian_culture_group [heritage] }
    male_common_first_names = {
        Aage Anders Andreas Anton Arne Axel Bjorn Carl Christian Christofer Daniel Edvard Einar Erik Folke Frederik Georg Gustav Hans Henrik Ivar Jacob Johan Julius Karl Knud Lars Ludvig Magnus Michael Niels Olaf Olav Ole Oscar Otto Peter Poul Sigurd Sten Sven Thomas Thorvald Vilhelm
    }
    female_common_first_names = {
        Amalie Anna Anne Augusta Birgitta Brita Caroline Catharina Charlotta Christina Dagmar Dorothea Elisabeth Erika Eva Frederikke Hanna Helena Inga Ingrid Irene Johanna Karin Kerstin Kristina Louise Lovisa Margaretha Maria Martha Matilda Sofia Ulrika
    }
    noble_last_names = {
        af_Ugglas Anker Barnekow Beck-Friis Bjelke Brahe CederstrO_m De_Geer Gyllenstierna Hamilton Hermelin Kaas Koskull Lagerbjelke Leijonhufvud Lovenskiold Morner Nordenfalk Palmstierna Piper Raab Reventlow Rosenkrantz Sprengtporten Trolle von_Essen von_Fersen von_Holstein Wachtmeister Wedel-Jarlsberg
    }
    common_last_names = {
        Andersen Andersson Berg Berggren Bergstrom BillstrO_m Bjork Blomqvist Carlsen Carlsson Dahlberg Danielsson Ekman Eriksson Falsen Fredriksson Gustafsson Hansen Hansson Henriksson Holm Holmberg Johansson Jonsson Juul Karlsson Krogh Larsen Larsson Lindberg Lindgren Lindstrom Lundberg Lundgren Michaelsen Nielsen Nilsson Olsen Olsson Pedersen Persson Petersson Pettersson Samuelsson Sandberg Svensson
    }
    graphics = [graphics]
    ethnicities = {
        1 = [ethnicity]
    }
}""",
    "korean": """korean_[name]= {
    color= hsv{ 0.17 0.41 0.34 }
    religion = confucian
    traits = { korean_language [heritage] }
    male_common_first_names = {
        Bak Bong-haek Byeon Choi-ung Chwa-chin Don-in Gu Han Hong-jip Heong-gyo Jeong Jo Jung-yang Kown Mung-geun Ok Sang-ok Sim Won-yong Yi Yun
    }
    female_common_first_names = {
        Bingheogak Hwahyeop Hyoyu Ja-yeong Jeongildang Seonhui Sinjeong Sunghee Yeongsuhap Yunjidang
    }
    noble_last_names = {
        Bak Chang Choe Gang Gim Gwon Han Hong Jo Kim Ko Min Moon Na Namgung Park Shin Seong Seok Song Won Yi
    }
    common_last_names = {
        Bo Chung Guk Gyu Haung Hu Hwan Hyong Im Jip Mok Seo Seon Shinjong Si Sun Taek Yong
    }
    graphics = [graphics]
    ethnicities = {
        1 = [ethnicity]
    }
}""",
    "jewish": """jewish_[name]= {
    color= hsv{ 0.13 0.80 0.99 }
    religion = jewish
    traits = { jewish_group [heritage] }
    male_common_first_names = {
        Abraham Albert Baruch Benjamin Binyamin Daniel David Eli Gavriel Gerson Gustav Heinrich Hermann Ignatz Isaak Itzhak Jakob Jeremias Josef Julius Leonhard Michael Moshe Salomon Saul Shmuel Sigmund Simon Theodor Yosef
    }
    female_common_first_names = {
        Angela Alice Amalie Berta Emma Elsa Inez Irene Johanna Klara Karoline Minna Margarete Noemie Regine Ruth Sonia Zoe
    }
    noble_last_names = {
        Abrabanel Auerbach Austerlitz von_Bleichroeder Camondo Curiel Ephrussi Guenzburg von_Hofmannsthal von_Neumann Oppenheim Sassoon Zuckerkandl
    }
    common_last_names = {
        Abramovitch Ashkenazi Barak Bernstein Birnbaum Bloch Cantor Cardoso Cohen Disraeli Frank Friedlander Gaon Ginsberg Goldstein Halevi Horowitz Israel Jacobsohn Kagan Kaplan Klein Levin Levy Luria Maimon Montefiore Morgenstern Nathan Oren Peretz Rosenthal Sachs Schapiro Schwartz Weinstein Weiss
    }
    graphics = [graphics]
    ethnicities = {
        1 = [ethnicity]
    }
}""",
    "romanian": """romanian_[name]= {
    color= hsv{ 0.12 0.41 0.54 }
    religion = orthodox
    traits = { romanian_culture_group [heritage] }
    male_common_first_names = {
        Adrian Alexandru Andrei Anton Carol Constantin Cornel Daniel Dumitru Eugen Ferdinand Gheorghe Grigore Ioan Iosif Iulian Laurentiu Lucian Mihai Mircea Nicolae Octavian Ovidiu Petru Radu Sergiu Stefan Teodor Toma Traian Vasile Victor Vlad
    }
    female_common_first_names = {
        Adela Ana Constanta Daria Ecaterina Elena Elisa Elisabeta Eugenia Iulia Lucretia Maria
    }
    noble_last_names = {
        Asachi Cantemir Caradja Callimachi Ghica Hasdeu Hurmuzachi Kogalniceanu Moruzi Racovita Sturdza Vacarescu
    }
    common_last_names = {
        Angelescu Antonescu Argetoianu Averescu Bragadiru Cernat Coanda Culcer Cuza Dragalina Florescu Grigorescu Ionescu Lahovary Lupescu Manu Marinescu Murgescu Panaitescu Poenaru Popescu Prezan Samsonovici Steflea Tatarascu Vaitoianu
    }
    graphics = [graphics]
    ethnicities = {
        1 = [ethnicity]
    }
}""",
    "burmese": """burmese_[name]= {
    color= hsv{ 0.13 0.42 0.38 }
    religion = theravada
    traits = { burmese_language [heritage] }
    male_common_first_names = {
        Alaungphaya Bodawphaya Duwa Ga Hsinbyushin Hta Maung Mindon Minkyaw Naungdawkyi Pagan Sama Saw Singu Sinwa Thibaw U Zan
    }
    female_common_first_names = {
        Bawk_Ja Chandra Hsinbyumashin Nan_Moe_Moe Naw_Paw Supayalat Thaung Thin
    }
    noble_last_names = {
        Aung Kantarawadi Konbaung Lisu Min Mungchi Sao Shatam U_bee
    }
    common_last_names = {
        Bagyidaw Bandula Bye Che Dabayin Kye Kyi Lahpai Lahtaw Law_Paw Maran Myo Ne_Myo Papw Thura
    }
    graphics = [graphics]
    ethnicities = {
        1 = [ethnicity]
    }
}""",
    "tai": """tai_[name]= {
    color= hsv{ 0.61 0.29 0.58 }
    religion = theravada
    traits = { tai [heritage] }
    male_common_first_names = {
        Anurutha Chao Chulalongkorn Hkam Hkun Hseng Hso Lun Mongkut Nangklao Nanthasen Ong Phraya Sakkarin Setthathirath Shwe Sisavang Sun Than Tuam Unkham Vajiravudh
    }
    female_common_first_names = {
        Adorndibyanibha Bandhavanna Charm Hearn Kham-Oun Pheng Prabha Samathi Sirikit Valaya Yaovabha
    }
    noble_last_names = {
        Chakri Luang_Phrabang Ong Praya_Siri Sao
    }
    common_last_names = {
        Anuvong Bunnag Cheng Hmu Hung Inswang Kaw Kridakorn Kuman Letya Long Min Mong Nan Nitithada Phonphayuhasena Praband Rabibadhana Som Thephatsadin Vong
    }
    graphics = [graphics]
    ethnicities = {
        1 = [ethnicity]
    }
}""",
    "khmer": """khmer_[name]= {
    color= hsv{ 0.04 0.54 0.86 }
    religion = theravada
    traits = { khmer_language [heritage] }
    male_common_first_names = {
        Ang Laik-Gi Manthaturath Norodom Ong Pok Sakkarin Satha Sisowath Sukha Taksin Thommo Tun Unkeo
    }
    female_common_first_names = {
        Aut Bandhavanna Bunlei Di Mey Nokiang Ros Tuu Thiha Vanthy Vara
    }
    noble_last_names = {
        Ang Chakri Luang_Phrabang Ong Varman
    }
    common_last_names = {
        Anuvong Bun Chan Em Eng Intharavong Kuman Long Maung Mey Non Reachea Saw Sieng Sinn Snguon Soe Som Supho Tong Vong
    }
    graphics = [graphics]
    ethnicities = {
        1 = [ethnicity]
    }
}""",
    "polynesian": """polynesian_[name]= {
    color= hsv{ 0.73 0.49 0.65 }
    religion = animist
    traits = { polynesian_group [heritage] }
    male_common_first_names = {
        Finau [cite: 82] Iosefo [cite: 82] Kaoua [cite: 84] Kahanamoku [cite: 82] Lunalilo [cite: 82] Mahuta [cite: 85] Pokaia [cite: 85] Samuel [cite: 84] Seru [cite: 84] Taufa_ahau [cite: 82] Te_Rata [cite: 85] William [cite: 82]
    }
    female_common_first_names = {
        Alanieta [cite: 84] Auli_i [cite: 82] Hariata [cite: 85] Kahupeka [cite: 85] Kaliko [cite: 82] Kamamalu [cite: 82] Mary [cite: 82] Pane [cite: 82] Pomare [cite: 82] Salote [cite: 84] Sarojini [cite: 84] Te_Puea [cite: 85]
    }
    noble_last_names = {
        Dovi [cite: 84] Heke [cite: 85] Hongi [cite: 85] Kalakaua [cite: 82] Kamehameha [cite: 82] Kawananakoa [cite: 82] Pomare [cite: 82] Sukuna [cite: 84] Te_Wherowhero [cite: 85] Uluviti [cite: 84]
    }
    common_last_names = {
        Cakobau [cite: 84] Feletoa [cite: 82] Ielemia [cite: 82] Kahanamoku [cite: 83] Loganimoce [cite: 84] Ma_ufanga [cite: 82] Nakuina [cite: 83] Pukui [cite: 83] Raouparah [cite: 85] Tautu [cite: 84] Tupou [cite: 84] Wherowhero [cite: 85]
    }
    graphics = [graphics]
    ethnicities = {
        1 = [ethnicity]
    }
}""",
}

heritage_templates = {
    "european": {
        "heritage": "european_heritage",
        "ethnicity": "caucasian",
        "graphics": "european",
    },
    "african": {
        "heritage": "african_heritage",
        "ethnicity": "african",
        "graphics": "african",
    },
    "east_asian": {
        "heritage": "east_asian_heritage",
        "ethnicity": "asian",
        "graphics": "east_asian",
    },
    "west_asian": {
        "heritage": "middle_eastern_heritage",
        "ethnicity": "arab",
        "graphics": "arabic",
    },
    "indian": {
        "heritage": "south_asian_heritage",
        "ethnicity": "indian",
        "graphics": "south_asian",
    },
    "central_asian": {
        "heritage": "central_asian_heritage",
        "ethnicity": "central_asian",
        "graphics": "east_asian",
    },
    "indigenous_american": {
        "heritage": "indigenous_american_heritage",
        "ethnicity": "native_american",
        "graphics": "decentralised_americas",
    },
    "southeast_asian": {
        "heritage": "southeast_asian_heritage",
        "ethnicity": "indian",
        "graphics": "south_asian",
    },
    "oceanic": {
        "heritage": "indigenous_oceanic_heritage",
        "ethnicity": "polynesian",
        "graphics": "decentralised_americas",
    },
    "north_asian": {
        "heritage": "north_asian_heritage",
        "ethnicity": "asian",
        "graphics": "east_asian",
    },
}

name_trait_mapping = {
    "anglo": "anglophone",
    "franco": "francophone",
    "german": "german_speaking",
    "hispano": "hispanophone",
    "lusano": "lusophone",
    "italo": "italophone",
    "slavic": "east_slavic",
    "hellenic": "greek_culture",
    "arab": "arab_speaking",
    "sino": "sinosphere",
    "iranian": "iranian_turanian_culture_group",
    "dutch": "beneluxian_culture_group",
    "japanese": "yamato",
    "indo_aryan": "indo_aryan_language",
    "dravidian": "dravidian",
    "bantu": "bantu",
    "turkic": "turkic",
    "malay": "malay_culture",
    "north_american": "north_american_group",
    "mesoamerican": "native_mesoamerican_culture_group",
    "south_american": "south_american_group",
    "west_slavic": "west_slavic",
    "south_slavic": "jugoslav",
    "celtic": "celtic_people",
    "hungarian": "hungarian_culture_group",
    "scandinavian": "scandinavian_culture_group",
    "korean": "korean_language",
    "jewish": "jewish_group",
    "romanian": "romanian_culture_group",
    "burmese": "burmese_language",
    "tai": "tai",
    "khmer": "khmer_language",
    "polynesian": "polynesian_group",
}

heritage_base = {
    "anglo": "european_heritage",
    "franco": "european_heritage",
    "german": "european_heritage",
    "hispano": "european_heritage",
    "lusano": "european_heritage",
    "italo": "european_heritage",
    "slavic": "european_heritage",
    "hellenic": "european_heritage",
    "arab": "middle_eastern_heritage",
    "sino": "east_asian_heritage",
    "iranian": "iranian_turanian_culture_group",
    "dutch": "european_heritage",
    "japanese": "east_asian_heritage",
    "indo_aryan": "south_asian_heritage",
    "dravidian": "south_asian_heritage",
    "bantu": "african_heritage",
    "turkic": "central_asian_heritage",
    "malay": "southeast_asian_heritage",
    "north_american": "indigenous_american_heritage",
    "mesoamerican": "indigenous_american_heritage",
    "south_american": "indigenous_american_heritage",
    "west_slavic": "european_heritage",
    "south_slavic": "european_heritage",
    "celtic": "european_heritage",
    "hungarian": "european_heritage",
    "scandinavian": "european_heritage",
    "korean": "east_asian_heritage",
    "jewish": "european_heritage",
    "romanian": "european_heritage",
    "burmese": "southeast_asian_heritage",
    "tai": "southeast_asian_heritage",
    "khmer": "southeast_asian_heritage",
    "polynesian": "indigenous_oceanic_heritage",
}

# Provides specific, polished display names for culture templates.
display_name_map = {
    # Colonial/Linguistic Prefixes
    "anglo": "Anglo",
    "franco": "Franco",
    "german": "German",
    "hispano": "Hispano",
    "lusano": "Luso",
    "italo": "Italo",
    "dutch": "Dutch",
    "sino": "Sino",
    "japanese": "Japanese",
    # Indigenous American Groups
    # These are hard because the South American and (especially) North American cultures are very diverse.
    "north_american": "Akiin",
    "mesoamerican": "Mesoan",
    "south_american": "Ayllun",
    # Other Cultural Groups
    "slavic": "East Slavic",
    "hellenic": "Greek",
    "celtic": "Gaelic",
    "south_slavic": "South Slavic",
    "west_slavic": "West Slavic",
    "indo_aryan": "Indo-Aryan",
    "polynesian": "Polynesian",
}

# Configures the final name format using {culture} and {heritage} placeholders.
# This is more flexible than the old prefix/suffix system.
name_format_map = {
    # Prefix-style cultures
    "anglo": '"{culture}-{heritage}"',
    "franco": '"{culture}-{heritage}"',
    "german": '"{culture}-{heritage}"',
    "hispano": '"{culture}-{heritage}"',
    "lusano": '"{culture}-{heritage}"',
    "italo": '"{culture}-{heritage}"',
    "dutch": '"{culture}-{heritage}"',
    "sino": '"{culture}-{heritage}"',
    "japanese": '"{culture}-{heritage}"',
    # Suffix-style cultures (default for most)
    "default": '"{heritage}-{culture}"',
}

output = ""
for culture_template in culture_templates.keys():
    for heritage in heritage_templates.keys():
        if heritage_base[culture_template] != heritage_templates[heritage]["heritage"]:
            culture = (
                culture_templates[culture_template]
                .replace(
                    "[name]",
                    heritage,
                )
                .replace(
                    "[heritage]",
                    heritage_templates[heritage]["heritage"],
                )
                .replace("[ethnicity]", heritage_templates[heritage]["ethnicity"])
                .replace("[graphics]", heritage_templates[heritage]["graphics"])
            )
            output += culture + "\n\n"

with open(mod_path + r"\common\cultures\assimilation_cultures.txt", "w") as file:
    file.write(output)

on_action_template_existing = """        if = {
            limit = {
                is_incorporated = yes
                owner = {
                    NOR = {
                        has_law = law_type:law_minority_rights_violent_hostility
                        has_law = law_type:law_minority_rights_ghettoization
                    }
                    any_primary_culture = {
                        has_discrimination_trait = [heritage]
                    }
                }
                any_scope_pop = {
                    culture = {
                        has_discrimination_trait = [heritage]
                        NOT = { has_homeland = ROOT }
                    }
                    pop_acceptance >= 20
                    NOT = { has_ongoing_assimilation = yes }
                }
                NOT = {
                    any_scope_pop = {
                        pop_has_primary_culture = yes
                        culture = {
                            has_discrimination_trait = [heritage]
                        }
                    }
                }
            }
            every_scope_pop = {
                limit = {
                    culture = {
                        has_discrimination_trait = [heritage]
                        NOT = { has_homeland = ROOT }
                    }
                    pop_acceptance >= 20
                    NOT = { has_ongoing_assimilation = yes }
                }
                owner = {
                    random_primary_culture = {
                        limit = {
                            has_discrimination_trait = [heritage]
                        }
                        save_scope_as = target_culture
                    }
                }
                change_pop_culture = {
                    target = scope:target_culture
                    value = 0.01
                }
            }
        }
"""

on_action_template_new = """        if = {
            limit = {
                is_incorporated = yes
                owner = {
                    any_primary_culture = {
                        has_discrimination_trait = [trait]
                    }
                    NOR = {
                        has_law = law_type:law_minority_rights_violent_hostility
                        has_law = law_type:law_minority_rights_ghettoization
                    }
                    NOT = {
                        any_primary_culture = {
                            has_discrimination_trait = [heritage]
                        }
                    }
                }
                any_scope_pop = {
                    culture = {
                        has_discrimination_trait = [heritage]
                        NOT = { has_homeland = ROOT }
                        NOT = { has_discrimination_trait = [trait] }
                    }
                    pop_acceptance >= 20
                    NOT = { has_ongoing_assimilation = yes }
                }
            }
            every_scope_pop = {
                limit = {
                    culture = {
                        has_discrimination_trait = [heritage]
                        NOT = { has_homeland = ROOT }
                        NOT = { has_discrimination_trait = [trait] }
                    }
                    pop_acceptance >= 20
                    NOT = { has_ongoing_assimilation = yes }
                }
                change_pop_culture = {
                    target = cu:[target_culture]
                    value = pop_culture_conversion_propotion_script_value
                }
            }
        }
"""

on_action_output = """
on_monthly_pulse_state = {
    on_actions = {
        assimilation_on_action
    }
}

assimilation_on_action = {
    effect = {
[all_on_action_segments]
    }
}"""

all_on_action_segments = ""

for culture_template in culture_templates.keys():
    for heritage in heritage_templates.keys():
        if heritage_base[culture_template] != heritage_templates[heritage]["heritage"]:
            culture_segment = (
                on_action_template_new.replace(
                    "[trait]",
                    name_trait_mapping[culture_template],
                )
                .replace(
                    "[heritage]",
                    heritage_templates[heritage]["heritage"],
                )
                .replace("[target_culture]", culture_template + "_" + heritage)
            )
            all_on_action_segments += culture_segment + "\n"

for heritage in heritage_templates.keys():
    culture_segment = on_action_template_existing.replace(
        "[heritage]",
        heritage_templates[heritage]["heritage"],
    )
    all_on_action_segments += culture_segment + "\n"

with open(mod_path + r"\common\on_actions\assimilation_on_action.txt", "w") as file:
    file.write(
        on_action_output.replace("[all_on_action_segments]", all_on_action_segments)
    )

localization_output = "l_english:\n"
for culture_template in culture_templates.keys():
    for heritage in heritage_templates.keys():
        if heritage_base[culture_template] != heritage_templates[heritage]["heritage"]:
            # 1. Get the format string for the culture, or use the default
            format_string = name_format_map.get(
                culture_template, name_format_map["default"]
            )

            # 2. Get the polished display name for the new culture
            culture_formatted_name = display_name_map.get(
                culture_template, " ".join(culture_template.split("_")).title()
            )

            # 3. Get the formatted name for the old heritage
            heritage_formatted_name = " ".join(heritage.split("_")).title()

            # 4. Apply the format string to generate the final name
            final_name = format_string.format(
                culture=culture_formatted_name, heritage=heritage_formatted_name
            )

            localization_output += f" {culture_template}_{heritage}:0 {final_name}\n"

with open(
    mod_path + r"\localization\english\assimilation_cultures_l_english.yml",
    "w",
    encoding="utf-8-sig",
) as file:
    file.write(localization_output)

print("Done!")
