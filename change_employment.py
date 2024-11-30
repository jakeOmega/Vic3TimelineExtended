# -*- coding: utf-8 -*-
"""
Created on Fri Jul 21 19:18:23 2023

@author: jakef
"""

old_text = """pm_one_room_schoolhouses  = {
	texture = "gfx/interface/icons/production_method_icons/scholastic_education.dds"

	building_modifiers = {
		workforce_scaled = {
			# input goods
			goods_input_paper_add = 50
			goods_input_services_add = 10
			goods_input_transportation_add = 10
			goods_output_educational_services_add = 50
		}
	}
}

pm_standardized_education_system = {
	texture = "gfx/interface/icons/production_method_icons/scholastic_education.dds"
	
	unlocking_technologies = {
		psychiatry
	}
	
	unlocking_laws = {
		law_restricted_child_labor
		law_compulsory_primary_school
	}

	building_modifiers = {
		workforce_scaled = {
			# input goods
			goods_input_paper_add = 50
			goods_input_services_add = 15
			goods_input_transportation_add = 15
			goods_output_educational_services_add = 75
		}
	}
}
 
pm_mass_public_education = {
	texture = "gfx/interface/icons/production_method_icons/scholastic_education.dds"
	
	unlocking_technologies = {
		central_planning
	}
	
	unlocking_laws = {
		law_compulsory_primary_school
	}

	building_modifiers = {
		workforce_scaled = {
			# input goods
			goods_input_paper_add = 50
			goods_input_services_add = 25
			goods_input_transportation_add = 25
			goods_input_electricity_add = 25
			goods_output_educational_services_add = 125
		}
	}
}

pm_computer_assisted_learning = {
	texture = "gfx/interface/icons/production_method_icons/scholastic_education.dds"
	
	unlocking_technologies = {
		home_video_systems
	}
	
	unlocking_laws = {
		law_compulsory_primary_school
	}

	building_modifiers = {
		workforce_scaled = {
			# input goods
			goods_input_paper_add = 50
			goods_input_services_add = 25
			goods_input_transportation_add = 25
			goods_input_electricity_add = 25
			goods_input_consumer_appliances_add = 25
			goods_input_digital_access_add = 10
			goods_input_telephones_add = 10
			goods_input_radios_add = 5
			goods_output_educational_services_add = 200
		}
	}
}

pm_individualized_learning = {
	texture = "gfx/interface/icons/production_method_icons/scholastic_education.dds"
	
	unlocking_technologies = {
		digital_education
	}
	
	unlocking_laws = {
		law_compulsory_primary_school
	}

	building_modifiers = {
		workforce_scaled = {
			# input goods
			goods_input_paper_add = 50
			goods_input_services_add = 25
			goods_input_transportation_add = 25
			goods_input_electricity_add = 25
			goods_input_consumer_appliances_add = 25
			goods_input_digital_access_add = 50
			goods_input_telephones_add = 25
			goods_input_radios_add = 25
			goods_output_educational_services_add = 300
		}
	}
}

pm_neuro-enhanced_learning = {
	texture = "gfx/interface/icons/production_method_icons/scholastic_education.dds"
	
	unlocking_technologies = {
		biohacking_and_human_augmentation
	}
	
	unlocking_laws = {
		law_compulsory_primary_school
	}

	building_modifiers = {
		workforce_scaled = {
			# input goods
			goods_input_paper_add = 50
			goods_input_services_add = 25
			goods_input_transportation_add = 25
			goods_input_electricity_add = 25
			goods_input_consumer_appliances_add = 25
			goods_input_digital_access_add = 50
			goods_input_telephones_add = 25
			goods_input_radios_add = 25
			goods_input_advanced_materials_add = 2.5
			goods_output_educational_services_add = 400
		}
	}
}

pm_religious_education_I = {
	texture = "gfx/interface/icons/production_method_icons/scholastic_education.dds"
	
	unlocking_production_methods = {
		pm_individualized_learning 
		pm_neuro-enhanced_learning
		pm_mass_public_education 
		pm_computer_assisted_learning 
		pm_one_room_schoolhouses
		pm_standardized_education_system
	}
	
	unlocking_laws = {
		law_religious_schools
	}
	
	is_hidden_when_unavailable = yes

	state_modifiers = {
		workforce_scaled = {
			state_conversion_mult = 1
			state_education_access_add = 0.5
		}
		level_scaled = {
			building_employment_clergymen_add = 500
			building_employment_academics_add = 250
			building_employment_clerks_add = 500
		}
	}
}

pm_private_education_I = {
	texture = "gfx/interface/icons/production_method_icons/scholastic_education.dds"
	
	unlocking_production_methods = {
		pm_individualized_learning 
		pm_neuro-enhanced_learning
		pm_mass_public_education 
		pm_computer_assisted_learning 
		pm_one_room_schoolhouses
		pm_standardized_education_system
	}
	
	unlocking_laws = {
		law_private_schools
	}
	
	is_hidden_when_unavailable = yes

	state_modifiers = {
		workforce_scaled = {
			state_education_access_wealth_add = 0.025
		}
		level_scaled = {
			building_employment_academics_add = 750
			building_employment_clerks_add = 500
		}
	}
}

pm_public_education_I = {
	texture = "gfx/interface/icons/production_method_icons/scholastic_education.dds"
	
	unlocking_production_methods = {
		pm_individualized_learning 
		pm_neuro-enhanced_learning
		pm_mass_public_education 
		pm_computer_assisted_learning 
		pm_one_room_schoolhouses
		pm_standardized_education_system
	}
	
	unlocking_laws = {
		law_public_schools
	}
	
	is_hidden_when_unavailable = yes

	state_modifiers = {
		workforce_scaled = {
			state_assimilation_mult = 0.625
			state_education_access_add = 0.5
		}
		level_scaled = {
			building_employment_bureaucrats_add = 250
			building_employment_academics_add = 500
			building_employment_clerks_add = 500
		}
	}
	
	building_modifiers = {
		unscaled = {
			building_government_shares_add = 1
		}
	}
}

pm_religious_education_II = {
	texture = "gfx/interface/icons/production_method_icons/scholastic_education.dds"
	
	unlocking_production_methods = {
		pm_individualized_learning 
		pm_neuro-enhanced_learning
		pm_mass_public_education 
		pm_computer_assisted_learning 
	}
	
	unlocking_laws = {
		law_religious_schools
	}
	
	is_hidden_when_unavailable = yes

	state_modifiers = {
		workforce_scaled = {
			state_conversion_mult = 1.5
			state_education_access_add = 0.75
		}
		level_scaled = {
			building_employment_clergymen_add = 500
			building_employment_academics_add = 250
			building_employment_clerks_add = 500
		}
	}
}

pm_private_education_II = {
	texture = "gfx/interface/icons/production_method_icons/scholastic_education.dds"
	
	unlocking_production_methods = {
		pm_individualized_learning 
		pm_neuro-enhanced_learning
		pm_mass_public_education 
		pm_computer_assisted_learning 
	}
	
	unlocking_laws = {
		law_private_schools
	}
	
	is_hidden_when_unavailable = yes

	state_modifiers = {
		workforce_scaled = {
			state_education_access_wealth_add = 0.0375
		}
		level_scaled = {
			building_employment_academics_add = 750
			building_employment_clerks_add = 500
		}
	}
}

pm_public_education_II = {
	texture = "gfx/interface/icons/production_method_icons/scholastic_education.dds"
	
	unlocking_production_methods = {
		pm_individualized_learning 
		pm_neuro-enhanced_learning
		pm_mass_public_education 
		pm_computer_assisted_learning 
	}
	
	unlocking_laws = {
		law_public_schools
	}
	
	is_hidden_when_unavailable = yes

	state_modifiers = {
		workforce_scaled = {
			state_assimilation_mult = 0.875
			state_education_access_add = 0.75
		}
		level_scaled = {
			building_employment_bureaucrats_add = 250
			building_employment_academics_add = 500
			building_employment_clerks_add = 500
		}
	}
	
	building_modifiers = {
		unscaled = {
			building_government_shares_add = 1
		}
	}
}

pm_religious_education_III = {
	texture = "gfx/interface/icons/production_method_icons/scholastic_education.dds"
	
	unlocking_production_methods = {
		pm_individualized_learning 
		pm_neuro-enhanced_learning
	}
	
	unlocking_laws = {
		law_religious_schools
	}
	
	is_hidden_when_unavailable = yes

	state_modifiers = {
		workforce_scaled = {
			state_conversion_mult = 2
			state_education_access_add = 1
		}
		level_scaled = {
			building_employment_clergymen_add = 500
			building_employment_academics_add = 250
			building_employment_clerks_add = 500
		}
	}
}

pm_private_education_III = {
	texture = "gfx/interface/icons/production_method_icons/scholastic_education.dds"
	
	unlocking_production_methods = {
		pm_individualized_learning 
		pm_neuro-enhanced_learning
	}
	
	unlocking_laws = {
		law_private_schools
	}
	
	is_hidden_when_unavailable = yes

	state_modifiers = {
		workforce_scaled = {
			state_education_access_wealth_add = 0.05
		}
		level_scaled = {
			building_employment_academics_add = 750
			building_employment_clerks_add = 500
		}
	}
}

pm_public_education_III = {
	texture = "gfx/interface/icons/production_method_icons/scholastic_education.dds"
	
	unlocking_production_methods = {
		pm_individualized_learning 
		pm_neuro-enhanced_learning
	}
	
	unlocking_laws = {
		law_public_schools
	}
	
	is_hidden_when_unavailable = yes

	state_modifiers = {
		workforce_scaled = {
			state_assimilation_mult = 1.25
			state_education_access_add = 1
		}
		level_scaled = {
			building_employment_bureaucrats_add = 250
			building_employment_academics_add = 500
			building_employment_clerks_add = 500
		}
	}
	
	building_modifiers = {
		unscaled = {
			building_government_shares_add = 1
		}
	}
}

pm_apothecaries = {
	texture = "gfx/interface/icons/production_method_icons/unused/apothecaries.dds"

	building_modifiers = {
		workforce_scaled = {
			# input goods
			goods_input_grain_add = 20
			goods_input_glass_add = 10
			goods_input_wood_add = 10
			goods_input_sulfur_add = 10
			goods_output_healthcare_services_add = 50
		}
	}
}

pm_systematic_disease_control = {
	texture = "gfx/interface/icons/production_method_icons/scholastic_education.dds"
	
	unlocking_technologies = {
		quinine
	}

	building_modifiers = {
		workforce_scaled = {
			# input goods
			goods_input_grain_add = 20
			goods_input_glass_add = 20
			goods_input_wood_add = 10
			goods_input_sulfur_add = 10
			goods_input_services_add = 15
			goods_output_healthcare_services_add = 75
			state_mortality_mult = -0.01
		}
	}
}

pm_antiseptics_and_anesthesia = {
	texture = "gfx/interface/icons/production_method_icons/scholastic_education.dds"
	
	unlocking_technologies = {
		malaria_prevention
	}

	building_modifiers = {
		workforce_scaled = {
			# input goods
			goods_input_grain_add = 20
			goods_input_glass_add = 20
			goods_input_sulfur_add = 20
			goods_input_services_add = 25
			goods_input_paper_add = 20
			goods_input_tools_add = 20
			goods_output_healthcare_services_add = 125
			state_mortality_mult = -0.02
		}
	}
}
pm_antibiotics_and_vaccines = {
	texture = "gfx/interface/icons/production_method_icons/scholastic_education.dds"
	
	unlocking_technologies = {
		modern_vaccines
	}

	building_modifiers = {
		workforce_scaled = {
			# input goods
			goods_input_grain_add = 30
			goods_input_glass_add = 30
			goods_input_sulfur_add = 30
			goods_input_services_add = 50
			goods_input_paper_add = 20
			goods_input_tools_add = 20
			goods_input_oil_add = 20
			goods_output_healthcare_services_add = 200
			state_mortality_mult = -0.03
		}
	}
}

pm_modern_medicine = {
	texture = "gfx/interface/icons/production_method_icons/scholastic_education.dds"
	
	unlocking_technologies = {
		modern_pharmaceuticals
	}

	building_modifiers = {
		workforce_scaled = {
			# input goods
			goods_input_grain_add = 40
			goods_input_glass_add = 40
			goods_input_sulfur_add = 30
			goods_input_services_add = 50
			goods_input_paper_add = 20
			goods_input_tools_add = 40
			goods_input_oil_add = 40
			goods_input_transportation_add = 20
			goods_input_electricity_add = 20
			goods_output_healthcare_services_add = 300
			state_mortality_mult = -0.04
		}
	}
}

pm_personalized_medicine = {
	texture = "gfx/interface/icons/production_method_icons/scholastic_education.dds"
	
	unlocking_technologies = {
		personalized_medicine
	}

	building_modifiers = {
		workforce_scaled = {
			# input goods
			goods_input_grain_add = 40
			goods_input_glass_add = 40
			goods_input_sulfur_add = 30
			goods_input_services_add = 50
			goods_input_paper_add = 20
			goods_input_tools_add = 40
			goods_input_oil_add = 40
			goods_input_transportation_add = 20
			goods_input_electricity_add = 50
			goods_input_digital_access_add = 20
			goods_input_consumer_appliances_add = 25
			goods_input_electronic_components_add = 25
			goods_output_healthcare_services_add = 400
			state_mortality_mult = -0.05
		}
	}
}

pm_nanotech_healthcare = {
	texture = "gfx/interface/icons/production_method_icons/scholastic_education.dds"
	
	unlocking_technologies = {
		biological_immortality
	}

	building_modifiers = {
		workforce_scaled = {
			# input goods
			goods_input_grain_add = 40
			goods_input_glass_add = 40
			goods_input_sulfur_add = 30
			goods_input_services_add = 50
			goods_input_paper_add = 20
			goods_input_tools_add = 40
			goods_input_oil_add = 40
			goods_input_transportation_add = 20
			goods_input_electricity_add = 50
			goods_input_digital_access_add = 20
			goods_input_consumer_appliances_add = 25
			goods_input_electronic_components_add = 25
			goods_input_advanced_materials_add = 10
			goods_output_healthcare_services_add = 1000
			state_mortality_mult = -0.08
		}
	}
}

pm_religious_health_I = {
	texture = "gfx/interface/icons/production_method_icons/scholastic_education.dds"
	
	unlocking_laws = {
		law_charitable_health_system
	}
	
	is_hidden_when_unavailable = yes

	state_modifiers = {
		workforce_scaled = {
			state_mortality_mult = -0.05
			state_mortality_wealth_mult = -0.005
		}
		level_scaled = {
			building_employment_clergymen_add = 500
			building_employment_academics_add = 250
			building_employment_clerks_add = 500
		}
	}
}

pm_private_health_I = {
	texture = "gfx/interface/icons/production_method_icons/scholastic_education.dds"
	
	unlocking_laws = {
		law_private_health_insurance
	}
	
	is_hidden_when_unavailable = yes

	state_modifiers = {
		workforce_scaled = {
			state_mortality_wealth_mult = -0.01
		}
		level_scaled = {
			building_employment_shopkeepers_add = 250
			building_employment_academics_add = 250
			building_employment_clerks_add = 750
		}
	}
}

pm_public_health_I = {
	texture = "gfx/interface/icons/production_method_icons/scholastic_education.dds"
	
	unlocking_laws = {
		law_public_health_insurance
	}
	
	is_hidden_when_unavailable = yes
	
	building_modifiers = {
		unscaled = {
			building_government_shares_add = 1
		}
	}

	state_modifiers = {
		workforce_scaled = {
			state_mortality_mult = -0.1
		}
		level_scaled = {
			building_employment_bureaucrats_add = 250
			building_employment_academics_add = 500
			building_employment_clerks_add = 500
		}
	}
}

pm_religious_health_II = {
	texture = "gfx/interface/icons/production_method_icons/scholastic_education.dds"
	
	unlocking_technologies = {
		antibiotics
	}
	
	unlocking_laws = {
		law_charitable_health_system
	}
	
	is_hidden_when_unavailable = yes

	state_modifiers = {
		workforce_scaled = {
			state_mortality_mult = -0.1
			state_mortality_wealth_mult = -0.01
		}
		level_scaled = {
			building_employment_clergymen_add = 500
			building_employment_academics_add = 250
			building_employment_clerks_add = 500
		}
	}
}

pm_private_health_II = {
	texture = "gfx/interface/icons/production_method_icons/scholastic_education.dds"
	
	unlocking_technologies = {
		antibiotics
	}
	
	unlocking_laws = {
		law_private_health_insurance
	}
	
	is_hidden_when_unavailable = yes

	state_modifiers = {
		workforce_scaled = {
			state_mortality_wealth_mult = -0.02
		}
		level_scaled = {
			building_employment_shopkeepers_add = 250
			building_employment_academics_add = 250
			building_employment_clerks_add = 750
		}
	}
}

pm_public_health_II = {
	texture = "gfx/interface/icons/production_method_icons/scholastic_education.dds"
	
	unlocking_technologies = {
		antibiotics
	}
	
	unlocking_laws = {
		law_public_health_insurance
	}
	
	is_hidden_when_unavailable = yes
	
	building_modifiers = {
		unscaled = {
			building_government_shares_add = 1
		}
	}

	state_modifiers = {
		workforce_scaled = {
			state_mortality_mult = -0.2
		}
		level_scaled = {
			building_employment_bureaucrats_add = 250
			building_employment_academics_add = 500
			building_employment_clerks_add = 500
		}
	}
}

pm_religious_health_III = {
	texture = "gfx/interface/icons/production_method_icons/scholastic_education.dds"
	
	unlocking_technologies = {
		antibiotic_mass_production
	}
	
	unlocking_laws = {
		law_charitable_health_system
	}
	
	is_hidden_when_unavailable = yes

	state_modifiers = {
		workforce_scaled = {
			state_mortality_mult = -0.15
			state_mortality_wealth_mult = -0.015
		}
		level_scaled = {
			building_employment_clergymen_add = 500
			building_employment_academics_add = 250
			building_employment_clerks_add = 500
		}
	}
}

pm_private_health_III = {
	texture = "gfx/interface/icons/production_method_icons/scholastic_education.dds"
	
	unlocking_technologies = {
		antibiotic_mass_production
	}
	
	unlocking_laws = {
		law_private_health_insurance
	}
	
	is_hidden_when_unavailable = yes

	state_modifiers = {
		workforce_scaled = {
			state_mortality_wealth_mult = -0.03
		}
		level_scaled = {
			building_employment_shopkeepers_add = 250
			building_employment_academics_add = 250
			building_employment_clerks_add = 750
		}
	}
}

pm_public_health_III = {
	texture = "gfx/interface/icons/production_method_icons/scholastic_education.dds"
	
	unlocking_technologies = {
		antibiotic_mass_production
	}
	
	unlocking_laws = {
		law_public_health_insurance
	}
	
	is_hidden_when_unavailable = yes
	
	building_modifiers = {
		unscaled = {
			building_government_shares_add = 1
		}
	}

	state_modifiers = {
		workforce_scaled = {
			state_mortality_mult = -0.3
		}
		level_scaled = {
			building_employment_bureaucrats_add = 250
			building_employment_academics_add = 500
			building_employment_clerks_add = 500
		}
	}
}

pm_religious_health_IV = {
	texture = "gfx/interface/icons/production_method_icons/scholastic_education.dds"
	
	unlocking_technologies = {
		telemedicine
	}
	
	unlocking_laws = {
		law_charitable_health_system
	}
	
	is_hidden_when_unavailable = yes

	state_modifiers = {
		workforce_scaled = {
			state_mortality_mult = -0.2
			state_mortality_wealth_mult = -0.02
		}
		level_scaled = {
			building_employment_clergymen_add = 500
			building_employment_academics_add = 250
			building_employment_clerks_add = 500
		}
	}
}

pm_private_health_IV = {
	texture = "gfx/interface/icons/production_method_icons/scholastic_education.dds"
	
	unlocking_technologies = {
		telemedicine
	}
	
	unlocking_laws = {
		law_private_health_insurance
	}
	
	is_hidden_when_unavailable = yes

	state_modifiers = {
		workforce_scaled = {
			state_mortality_wealth_mult = -0.04
		}
		level_scaled = {
			building_employment_shopkeepers_add = 250
			building_employment_academics_add = 250
			building_employment_clerks_add = 750
		}
	}
}

pm_public_health_IV = {
	texture = "gfx/interface/icons/production_method_icons/scholastic_education.dds"
	
	unlocking_technologies = {
		telemedicine
	}
	
	unlocking_laws = {
		law_public_health_insurance
	}
	
	is_hidden_when_unavailable = yes
	
	building_modifiers = {
		unscaled = {
			building_government_shares_add = 1
		}
	}

	state_modifiers = {
		workforce_scaled = {
			state_mortality_mult = -0.4
		}
		level_scaled = {
			building_employment_bureaucrats_add = 250
			building_employment_academics_add = 500
			building_employment_clerks_add = 500
		}
	}
}

pm_religious_health_V = {
	texture = "gfx/interface/icons/production_method_icons/scholastic_education.dds"
	
	unlocking_technologies = {
		personalized_medicine
	}
	
	unlocking_laws = {
		law_charitable_health_system
	}
	
	is_hidden_when_unavailable = yes

	state_modifiers = {
		workforce_scaled = {
			state_mortality_mult = -0.25
			state_mortality_wealth_mult = -0.025
		}
		level_scaled = {
			building_employment_clergymen_add = 500
			building_employment_academics_add = 250
			building_employment_clerks_add = 500
		}
	}
}

pm_private_health_V = {
	texture = "gfx/interface/icons/production_method_icons/scholastic_education.dds"
	
	unlocking_technologies = {
		personalized_medicine
	}
	
	unlocking_laws = {
		law_private_health_insurance
	}
	
	is_hidden_when_unavailable = yes

	state_modifiers = {
		workforce_scaled = {
			state_mortality_wealth_mult = -0.05
		}
		level_scaled = {
			building_employment_shopkeepers_add = 250
			building_employment_academics_add = 250
			building_employment_clerks_add = 750
		}
	}
}

pm_public_health_V = {
	texture = "gfx/interface/icons/production_method_icons/scholastic_education.dds"
	
	unlocking_technologies = {
		personalized_medicine
	}
	
	unlocking_laws = {
		law_public_health_insurance
	}
	
	is_hidden_when_unavailable = yes
	
	building_modifiers = {
		unscaled = {
			building_government_shares_add = 1
		}
	}

	state_modifiers = {
		workforce_scaled = {
			state_mortality_mult = -0.5
		}
		level_scaled = {
			building_employment_bureaucrats_add = 250
			building_employment_academics_add = 500
			building_employment_clerks_add = 500
		}
	}
}

pm_religious_health_VI = {
	texture = "gfx/interface/icons/production_method_icons/scholastic_education.dds"
	
	unlocking_technologies = {
		mind_backups
	}
	
	unlocking_laws = {
		law_charitable_health_system
	}
	
	is_hidden_when_unavailable = yes

	state_modifiers = {
		workforce_scaled = {
			state_mortality_mult = -0.3
			state_mortality_wealth_mult = -0.03
		}
		level_scaled = {
			building_employment_clergymen_add = 500
			building_employment_academics_add = 250
			building_employment_clerks_add = 500
		}
	}
}

pm_private_health_VI = {
	texture = "gfx/interface/icons/production_method_icons/scholastic_education.dds"
	
	unlocking_technologies = {
		mind_backups
	}
	
	unlocking_laws = {
		law_private_health_insurance
	}
	
	is_hidden_when_unavailable = yes

	state_modifiers = {
		workforce_scaled = {
			state_mortality_wealth_mult = -0.06
		}
		level_scaled = {
			building_employment_shopkeepers_add = 250
			building_employment_academics_add = 250
			building_employment_clerks_add = 750
		}
	}
}

pm_public_health_VI = {
	texture = "gfx/interface/icons/production_method_icons/scholastic_education.dds"
	
	unlocking_technologies = {
		mind_backups
	}
	
	unlocking_laws = {
		law_public_health_insurance
	}
	
	
	
	is_hidden_when_unavailable = yes
	
	building_modifiers = {
		unscaled = {
			building_government_shares_add = 1
		}
	}

	state_modifiers = {
		workforce_scaled = {
			state_mortality_mult = -0.6
		}
		level_scaled = {
			building_employment_bureaucrats_add = 250
			building_employment_academics_add = 500
			building_employment_clerks_add = 500
		}
	}
}

pm_watchmen = {
	texture = "gfx/interface/icons/production_method_icons/unused/secret_police_recruitment.dds"

	building_modifiers = {
		workforce_scaled = {
			# input goods
			goods_input_services_add = 5
			goods_input_small_arms_add = 5
			goods_output_security_services_add = 10
		}
	}
}

pm_uniformed_police = {
	texture = "gfx/interface/icons/production_method_icons/unused/secret_police_recruitment.dds"

	unlocking_technologies = {
		central_archives
	}

	building_modifiers = {
		workforce_scaled = {
			# input goods
			goods_input_ammunition_add = 5
			goods_input_small_arms_add = 5
			goods_input_clothes_add = 5
			goods_output_security_services_add = 15
		}
	}
}

pm_centralized_police_departments = {
	texture = "gfx/interface/icons/production_method_icons/unused/secret_police_recruitment.dds"

	unlocking_technologies = {
		identification_documents
	}

	building_modifiers = {
		workforce_scaled = {
			# input goods
			goods_input_services_add = 5
			goods_input_small_arms_add = 5
			goods_input_clothes_add = 5
			goods_input_ammunition_add = 5
			goods_input_paper_add = 5
			goods_output_security_services_add = 25
		}
	}
}
pm_surveillance_and_analytics = {
	texture = "gfx/interface/icons/production_method_icons/unused/secret_police_recruitment.dds"

	unlocking_technologies = {
		mass_surveillance
	}

	building_modifiers = {
		workforce_scaled = {
			# input goods
			goods_input_services_add = 5
			goods_input_small_arms_add = 5
			goods_input_clothes_add = 5
			goods_input_transportation_add = 5
			goods_input_paper_add = 5
			goods_input_electricity_add = 5
			goods_input_ammunition_add = 5
			goods_output_security_services_add = 40
		}
	}
}

pm_predictive_policing = {
	texture = "gfx/interface/icons/production_method_icons/unused/secret_police_recruitment.dds"

	unlocking_technologies = {
		cybersecurity
	}

	building_modifiers = {
		workforce_scaled = {
			# input goods
			goods_input_services_add = 5
			goods_input_small_arms_add = 5
			goods_input_clothes_add = 5
			goods_input_transportation_add = 5
			goods_input_paper_add = 5
			goods_input_electricity_add = 5
			goods_input_digital_access_add = 10
			goods_input_ammunition_add = 10
			goods_input_automobiles_add = 5
			goods_output_security_services_add = 60
		}
	}
}

pm_autonomous_security_systems = {
	texture = "gfx/interface/icons/production_method_icons/unused/secret_police_recruitment.dds"

	unlocking_technologies = {
		neural_lace
	}

	building_modifiers = {
		workforce_scaled = {
			# input goods
			goods_input_services_add = 5
			goods_input_small_arms_add = 5
			goods_input_clothes_add = 5
			goods_input_transportation_add = 5
			goods_input_paper_add = 5
			goods_input_electricity_add = 5
			goods_input_digital_access_add = 10
			goods_input_ammunition_add = 10
			goods_input_automobiles_add = 5
			goods_input_robotics_add = 10
			goods_output_security_services_add = 80
		}
	}
}

pm_local_police_I = {
	texture = "gfx/interface/icons/production_method_icons/unused/secret_police_recruitment.dds"
	
	unlocking_production_methods = {
		pm_watchmen
		pm_uniformed_police
	}
	
	unlocking_laws = {
		law_local_police
	}
	
	is_hidden_when_unavailable = yes

	state_modifiers = {
		workforce_scaled = {
			interest_group_ig_landowners_pol_str_mult = 0.50
			state_turmoil_effects_mult = -1
		}
		
		level_scaled = {
			building_employment_aristocrats_add = 50
			building_employment_laborers_add = 200
			building_employment_clerks_add = 250
			building_employment_officers_add = 125
		}
	}
}

pm_dedicated_police_I = {
	texture = "gfx/interface/icons/production_method_icons/unused/secret_police_recruitment.dds"
	
	unlocking_production_methods = {
		pm_watchmen
		pm_uniformed_police
	}
	
	unlocking_laws = {
		law_dedicated_police
	}
	
	is_hidden_when_unavailable = yes

	state_modifiers = {
		workforce_scaled = {
			state_radicals_from_political_movements_mult = -0.25
			state_turmoil_effects_mult = -0.75
		}
		
		level_scaled = {
			building_employment_soldiers_add = 125
			building_employment_laborers_add = 125
			building_employment_clerks_add = 250
			building_employment_officers_add = 125
		}
	}
}

pm_militarized_police_I = {
	texture = "gfx/interface/icons/production_method_icons/unused/secret_police_recruitment.dds"
	
	unlocking_production_methods = {
		pm_watchmen
		pm_uniformed_police
	}
	
	unlocking_laws = {
		law_militarized_police
	}
	
	is_hidden_when_unavailable = yes

	state_modifiers = {
		workforce_scaled = {
			state_radicals_from_political_movements_mult = -0.25
			state_radicals_from_discrimination_mult = -0.25
			interest_group_ig_armed_forces_pol_str_mult = 0.50
			state_mortality_turmoil_mult = 0.020
			state_turmoil_effects_mult = -0.75
		}

		level_scaled = {
			building_employment_soldiers_add = 250
			building_employment_clerks_add = 250
			building_employment_officers_add = 125
		}
	}
}

pm_public_police = {
	texture = "gfx/interface/icons/production_method_icons/scholastic_education.dds"

	building_modifiers = {
		unscaled = {
			building_government_shares_add = 1
		}
	}
}

pm_private_police = {
	texture = "gfx/interface/icons/production_method_icons/scholastic_education.dds"
}
"""

import re

employment_pattern = r"(building_employment_[a-z_]*_add\s=\s)(\d+)"
goods_input_pattern = r"(goods_input_[a-z_]*_add\s=\s)(\d+)"
goods_output_pattern = r"(goods_output_[a-z_]*_add\s=\s)(\d+)"


def adjust_numbers(text, multiplier, pattern, rounder):
    # The pattern to find employment numbers in the text

    def replace_func(match):
        # The replacement function that is called for each match
        # match.group(0) is the whole match, match.group(1) is the prefix, match.group(2) is the number
        new_number = (
            round(int(match.group(2)) * multiplier / rounder) * rounder
        )  # adjust the number and round to nearest 100
        return match.group(1) + str(new_number)  # return the new string

    # Use the re.sub function to replace all matches in the text
    new_text = re.sub(pattern, replace_func, text)

    return new_text


new_text = adjust_numbers(old_text, 0.1, goods_input_pattern, 0.1)
new_text = adjust_numbers(new_text, 0.1, goods_output_pattern, 0.1)
new_text = adjust_numbers(new_text, 0.333333, employment_pattern, 50)
with open("temp_py_out.txt", "w") as f:
    f.write(new_text)
