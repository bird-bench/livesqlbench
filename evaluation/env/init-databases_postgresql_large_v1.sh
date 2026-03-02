#!/bin/bash
set -e

# Wait for PostgreSQL to be ready
until psql -U root -c '\l' 2>/dev/null; do
  >&2 echo "PostgreSQL is unavailable - waiting..."
  sleep 2
done

echo "PostgreSQL is ready!"

############################
# 0. Create template DB: sql_test_template
############################
echo "Creating template database: sql_test_template with UTF8 encoding (formerly sql_test)"
psql -U root -tc "SELECT 1 FROM pg_database WHERE datname='sql_test_template'" | grep -q 1 \
  || psql -U root -c "CREATE DATABASE sql_test_template WITH OWNER=root ENCODING='UTF8' TEMPLATE=template0;"

# Create schemas in sql_test_template
echo "Creating required schemas: test_schema and test_schema_2 in sql_test_template"
psql -U root -d sql_test_template -c "CREATE SCHEMA IF NOT EXISTS test_schema;"
psql -U root -d sql_test_template -c "CREATE SCHEMA IF NOT EXISTS test_schema_2;"

# Create hstore, citext extensions
echo "Creating hstore and citext extensions in sql_test_template..."
psql -U root -d sql_test_template -c "CREATE EXTENSION IF NOT EXISTS hstore;"
psql -U root -d sql_test_template -c "CREATE EXTENSION IF NOT EXISTS citext;"

# Set default_text_search_config
echo "Setting default_text_search_config to pg_catalog.english in sql_test_template..."
psql -U root -d sql_test_template -c "ALTER DATABASE sql_test_template SET default_text_search_config = 'pg_catalog.english';"

echo "NOTE: For two-phase transaction support, set 'max_prepared_transactions' > 0 in postgresql.conf."

############################
# 1. Define DB → tables mapping
############################
declare -A DATABASE_MAPPING=(
    ["solar_panel_large_template"]="panel_models plants inspection clients asset_manufacturers certifications technicians maintenance_procedures plant_panel_model plant_record spare_parts ppa_contracts inverter_models training_sessions environmental_reports compliance_audits weather_stations electrical_performance environmental_conditions mechanical_condition operational_metrics alert site_inventory energy_tariffs inverters technician_certifications session_attendance work_orders work_order_updates work_order_procedures work_order_parts_usage financial_ledger BatteryStorageUnits DroneFlightLogs GridInterconnectionEvents VegetationManagementLogs SafetyIncidentReports SupplyChainShipments EnergyGenerationForecasts ClientSupportTickets CleaningRobotTelemetry WarrantyClaimFilings BatteryThermalEvents DroneInspectionFindings GridEventSettlements VegetationTaskMaterials SafetyCorrectiveActions ShipmentTrackingUpdates ForecastAccuracyMetrics TicketResolutionSteps RobotPathObstacles ClaimAppealDocuments"
    ["virtual_idol_large_template"]="fans virtualidols membershipandspending interactions engagement commerceandcollection socialcommunity eventsandclub loyaltyandachievements retentionandinfluence additionalnotes preferencesandsettings supportandfeedback moderationandcompliance sponsors genres interest_tags platforms designers club_roles skills market_analysis_and_trends fan_technical_profile idol_training_and_development virtual_idol_lore_and_storylines idol_asset_management physics_simulation_data virtual_idol_performance_metrics streaming_session_logs virtual_idol_sponsorships idol_genre_map idol_skill_sets_map idol_content_platforms_map fan_club_roles_map fan_interest_tags_map fan_content_submission_details fan_collaboration_projects fan_sentiment_analysis idol_merchandise_details event_logistics_and_planning event_sponsors idol_fan_collaborations merchandise_designers_map VirtualRealitySessionTelemetry CopyrightInfringementReports AlgorithmRecommendationFeeds DigitalSkinTransactionHistory VoiceSynthesisQualityLogs FanArtAuctionBidLogs GlobalServerLatencyStats HologramProjectorMaintenance SocialSentimentTrendSnapshots CollaborativeSongWritingSessions VREyeTrackingHeatmaps CopyrightTakedownAppeals RecommendationClickstream SkinOwnershipCertificates SynthesizedVoiceFeedback AuctionPaymentSettlements ServerRegionalOutageLogs ProjectorBulbReplacementHistory SentimentKeywordTrends CoCreationRoyaltySplits"
    ["reverse_logistics_large_template"]="customers products orders returns quality_assessment return_processing financial_management case_management warehouses suppliers transportation_carriers disposal_vendors employees service_level_agreements fraud_detection_rules warehouse_staff_assignments product_component_details repair_parts_inventory product_supplier_link product_disposal_guidelines order_shipment_details carrier_supported_regions return_package_inspections customer_communication_logs case_escalation_records financial_transaction_audits return_fraud_flags refurbishment_job_logs liquidation_auction_lots carrier_invoice_reconciliations warehouse_climate_sensor_logs supplier_recovery_claims customer_appeals_records circular_economy_impact_reports automated_sorting_machine_events omnichannel_return_points return_packaging_inventory refurb_qa_checklists liquidation_buyer_feedback freight_audit_discrepancies environmental_alert_history vendor_credit_memos appeal_compliance_checks recycled_material_sales sorter_jam_incidents dropoff_location_audits packaging_compliance_certs"
    ["organ_transplant_large_template"]="Demographics Recipients_Demographics Medical_History HLA_Info Function_and_Recovery Clinical Recipients_Immunology Transplant_Matching Compatibility_Metrics Risk_Evaluation Allocation_Details Logistics Administrative_and_Review Data_Source_and_Quality Hospitals Surgeons Medications Complications Insurance_Plans Protocols Training_Programs Quality_Metrics Rehabilitation_Programs Support_Groups Medical_Teams Equipment Transportation Organ_Banks Surgeon_Hospital_Affiliations Team_Training_Participation Tissue_Samples Consent_Forms Emergency_Contacts Imaging_Studies Genetic_Markers Recipient_Medication_History Recipient_Support_Group_Membership PostOpICUMonitoring LogisticsTelemetry InsuranceClaimDetails SurgeonFatigueAnalysis PatientWearableTelemetry BiobankEnvironmentLogs RehabDailyProgress ClinicalTrialParticipation EthicsCommitteeReviews DonorFamilyServices PharmacyInventoryBatch GenomicSequencingRun PatientNutritionLog PsychosocialAssessment FacilityMaintenanceLog SimulationTrainingSession PatientEducationModule TelehealthSessionLog InterHospitalTransfer ComplianceAuditLog"
    ["cybermarket_pattern_large_template"]="markets vendors buyers products transactions transaction_products vendor_markets vendor_countries vendor_payment_methods communications connection_security risk_analytics alerts vendor_profile_details market_regulatory_audits buyer_risk_history product_attribute_metrics transaction_settlement_info vendor_social_media vendor_financial_history market_traffic_analytics product_review_feedback platform_availability_snapshots vendor_regulatory_licenses buyer_device_fingerprints connection_attack_surface risk_ml_feature_vectors alert_case_actions knowledge_graph_nodes tag_library product_review_tag_map currency_rate_history platform_policy_documents vendor_insurance_policies vendor_insurance_claims insurance_claim_evidence VendorComplianceAudits PlatformIncidentReports TransactionDisputeDetails BuyerSessionAnalytics VendorPerformanceMetrics PaymentProcessingEvents AlertEscalationHistory MarketCompetitorAnalysis RiskModelPredictions VendorShipmentTracking BuyerLoyaltyProgram PlatformServiceHealth PaymentFraudIndicators AlertResponseWorkflow DisputeArbitrationDetails MarketTrendAnalysis RiskModelCalibration VendorComplianceDocuments BuyerPurchasePatterns VendorInventorySnapshot"
    ["exchange_traded_funds_large_template"]="families exchanges categories sectors bond_ratings securities funds family_categories family_exchanges sector_allocations bond_allocations holdings performance annual_returns risk_metrics fund_operations_details exchange_extended_info family_business_metrics security_detailed_analytics sector_market_intelligence bond_rating_market_data portfolio_managers fund_manager_assignments investment_strategies fund_strategy_implementations regulatory_authorities fund_regulatory_compliance daily_nav_history holdings_changes_history fund_flow_history expense_evolution_history performance_benchmark_history style_factor_analytics liquidity_risk_analytics esg_integration_analytics competitive_positioning_analytics risk_attribution_analytics CorporateActionEvents MarketSentimentScores FundWholesaleDistribution PortfolioStressTestResults ShareholderVotingOutcomes AnalystResearchConsensus TradeExecutionAudit FundTaxEfficiencyMetrics AlternativeDataSignals OperationalRiskEvents SentimentTradingSignals CorporateActionImpactAnalysis DistributionPlatformMetrics StressScenarioParameters VotingPolicyAlignment AnalystEstimateRevisions ExecutionQualityMetrics TaxLotManagement AlternativeDataQuality RiskEventRemediation"
    ["labor_certification_applications_large_template"]="employer employer_poc attorney preparer worksite prevailing_wage cases case_attorney case_worksite emp_financials_details emp_diversity_metrics emp_compliance_audit worksite_environmental_metrics wage_history case_processing_timeline case_rfe_details visa_extension_request worker_profile worker_education worker_dependent worker_position_history  recruitment_campaign recruitment_campaign_worksite_link recruitment_campaign_case_link training_program training_program_worker_link attorney_case_specialization employer_benefit_package data_quality_log CaseDecisionAudit AttorneyPerformanceMetric WorkerSkillCertification EmployerLaborCondition CaseFraudIndicator WorksiteInspection WorkerHealthBenefit RecruitmentSourceAnalytic CaseCorrespondenceLog EmployerComplianceScore DecisionAuditAppeal AttorneyTrainingRecord SourceChannelPerformance CertificationVerificationLog LaborConditionAmendment FraudInvestigationAction InspectionRemediationTask BenefitClaimDetail ComplianceScoreHistory CorrespondenceResponseTracking VisaExtensionOutcome"
    ["mental_healths_large_template"]="Facilities Clinicians Patients AssessmentBasics Encounters AssessmentSymptomsAndRisk AssessmentSocialAndDiagnosis TreatmentBasics TreatmentOutcomes Medications MedicalDevices InsurancePlans TrainingPrograms QualityMetrics Suppliers MedicalTeams RehabPrograms Caregivers CommunityResources ClinicalTrials ComplianceRecords SystemLogs Appointments MedicalRecords LabResults ImagingStudies CarePlans EmergencyEvents BillingRecords PatientMedications ClinicianTeams PatientCaregivers FacilitySuppliers PatientClinicalTrials TelehealthSessions AmbulanceTransport DeviceTelemetry PrescriptionFulfillment GenomicSequencing FacilityOccupancyLog InsuranceClaimsProcessing DietaryLogs SurgicalProcedures GenomicVariantAnalysis PatientFeedbackSurveys TelehealthQualityMetrics AmbulanceMaintenanceLogs DeviceAlertHistory PharmacyInventoryTracking ClaimsAppealRecords FacilityStaffingLogs NutritionConsultations PostSurgicalRecovery FeedbackActionItems ClinicalPathwayAdherence"
    ["archeology_scan_large_template"]="projects personnel sites equipment skills equipment_manufacturers research_institutions pointcloud registration mesh processing spatial qualitycontrol features scans conservation environment artifacts project_budgets project_milestones project_stakeholders project_institution_partnership permits shipping_log software_licenses data_access_logs personnel_skills personnel_certifications geological_surveys sample_analysis ProjectExpenses ExcavationSessions ArtifactPhotography EquipmentMaintenance LabSampleProcessing SiteEnvironmentMonitoring FieldNotes ScanCalibration ConservationTreatments TransportLogistics ExpenseReceipts ExcavationFindings FieldNoteAttachments PhotoProcessingQueue MaintenancePartsUsage SampleContaminationLog EnvironmentAlertEvents TreatmentChemicalApplications CalibrationVerificationTests TransportConditionReadings ArtifactConditionAssessments"
    ["polar_equipment_large_template"]="EquipmentType Equipment Location OperationMaintenance PowerBattery EngineAndFluids Transmission ChassisAndVehicle Communication CabinEnvironment LightingAndSafety WaterAndWaste Scientific WeatherAndStructure ThermalSolarWindAndGrid StationEquipmentType EquipmentTypeDetail EquipmentSpecification EquipmentLifecycle EquipmentLocationHistory ScientificCalibrationSchedule SensorModel SensorModelMeasurementProfile EquipmentSensorMapping FuelingAndChargingEvent CrewMember Project CrewProjectAssignment MaintenanceTaskCatalog TaskCrewAssignment TransmissionDiagnosticEvent ChassisDynamicsEvent CommunicationLinkMetric SafetyInspection WaterTreatmentCycle EnergyGenerationLog EquipmentPerformanceLog BatteryChargeCycleLog EngineRuntimeSnapshot CrewCertificationRecord TransmissionServiceHistory LocationEnvironmentalLog CommunicationSessionLog CabinOccupancyEvent ScientificDataAcquisition EquipmentHealthAssessment MaintenanceWorkOrder BatteryDegradationAnalysis EngineEmissionMeasurement CrewTrainingSession TransmissionFluidAnalysis ScientificExperimentResult LocationWeatherObservation CommunicationQualityMetric CabinAirQualitySample MaintenancePartConsumption EquipmentAnomalyDetection"
    ["robot_fault_prediction_large_template"]="robot_record robot_details operation joint_performance joint_condition actuation_data mechanical_status system_controller maintenance_and_fault performance_and_safety technicians certifications technician_certifications maintenance_logs spare_parts_inventory maintenance_parts_usage workcells environmental_sensors environmental_readings end_effectors end_effector_attachment_log products materials product_materials production_orders production_log quality_inspections power_consumption_log simulation_models simulation_runs anomaly_detection_log vision_system_telemetry firmware_deployment_history supplier_shipments human_proximity_events vibration_spectral_analysis waste_recycling_log grid_load_optimization calibration_events incident_reports digital_twin_sync_log automated_defect_classification battery_thermal_management firmware_security_audit material_storage_environment operator_biometric_telemetry joint_lubrication_status effluent_chemical_analysis laser_tracker_verification liability_claim_assessments physics_engine_parameters"
    ["fake_account_large_template"]="platforms accounts profiles security_sessions content_activity network_metrics interaction_metrics behavioral_scores risk_and_moderation cluster_analysis account_clusters monitoring profile_demographics device_fingerprint_details sentiment_analysis_stats content_language_distribution interaction_topic_metrics account_audit_logs risk_event_history cluster_temporal_metrics ad_campaigns ad_campaign_performance subscription_packages partner_integrations feedback_items feedback_responses tags topics account_tags content_topics account_subscriptions account_integrations media_asset_details stream_quality_logs commerce_transactions ai_inference_traces ad_bid_auctions influencer_brand_deals user_gamification_stats customer_support_tickets cdn_edge_metrics moderation_case_files api_usage_metering transaction_dispute_evidence model_feedback_loops stream_buffer_events ad_conversion_attribution influencer_post_compliance cdn_traffic_spikes gamification_level_rewards ticket_message_metrics moderation_appeals_process api_quota_adjustments"
    ["residential_data_large_template"]="locations infrastructure service_types households properties transportation_assets amenities infrastructure_details household_demographics property_valuations education_facilities healthcare_facilities commercial_establishments environmental_data transportation_network crime_statistics utility_services skills_inventory service_categories transportation_modes energy_consumption waste_management financial_services community_engagement household_member_skills household_service_enrollment household_transportation_usage Healthcare_Equipment_Inventory Commercial_Energy_Efficiency Household_Telecomm_Metrix Education_Facility_Resources Public_Safety_Patrol_Logs Resilient_Infrastructure_Health Waste_Stream_Analysis Digital_Payment_Transactional_Flux Household_Skill_Progression Environmental_Microclimate_Sensors Hospital_Critical_Care_Telemetry Waste_Processing_Plant_Efficiency Industrial_HVAC_Sensor_Array Smart_Home_Bandwidth_Allocation Digital_Classroom_Engagement Emergency_Vehicle_Telematics Professional_Certification_Audit Bridge_Structural_Monitoring Merchant_Settlement_Audit Air_Quality_Health_Correlation Healthcare_Power_Resilience"
    ["disaster_relief_large_template"]="disasterevents operations distributionhubs SupplyItemCatalogue SkillCatalogue environmentandhealth beneficiariesandassessments coordinationandevaluation humanresources BeneficiaryHouseholds VolunteerProfiles supplies transportation VehicleMaintenanceLogs MemberProfiles Household_Member_Map TrainingSessions skill_Session_Map Volunteer_Skill_Map financials ShelterFacilities CommunityInfrastructureAssessments StakeholderEngagement DataAnalyticsReports EarlyWarningSystems LogisticsContracts CommunicationLogs DiseaseOutbreakMonitoring SupplyAllocation MediaCoverage OperationRiskAssessments operation_hub_map DisasterEventCore BeneficiaryCore VolunteerCore ShelterCore DistributionHubCore OperationCore TrainingSessionCore InfrastructureAssessmentCore DiseaseOutbreakCore DisasterResponseTeam EmergencyCommunicationLog ShelterOccupancyRecord BeneficiaryAssistanceRecord VolunteerDeployment OperationLogistics TrainingAttendance InfrastructureRepairLog DiseaseContainmentMeasure"
    ["museum_artifact_large_template"]="enum_definitions ArtifactsCore ExhibitionHalls Artists Exhibitions ConservationTreatments ArtifactPublicationLink MaterialAnalysis InsurancePolicies DigitalAssets Showcases Staff Researchers LendingInstitutions Publications ArtifactArtistLink ArtifactConservatorLink ArtifactProvenance EnvironmentalReadingsCore LightAndRadiationReadings AirQualityReadings SurfaceAndPhysicalReadings RiskAssessments UsageRecords ArtifactSecurityAccess Monitor_Showcase_Map ArtifactRatings ConditionAssessments SensitivityData ConservationAndMaintenance TransportationLog EmergencyPlans ArtifactProfile ShowcaseEnvironment ArtifactCondition ExhibitionSchedule ArtifactLoan ConservationTreatment ResearcherAccess SecurityIncident TransportationMonitor LightRadiationLog DigitalAssetLink PublicationRecord RiskAssessmentDetail AirQualityMonitor MaterialAnalysisLog InsurancePolicyDetail CorporateSponsorRecord EmergencyResponseLog ArtifactUsageLog ConservationMaintenanceLog"
    ["cross_border_large_template"]="DataFlow System_Inventory Control_Library Transfer_Mechanism Dataset_Catalog DataField_Catalog Geo_Jurisdiction Risk_Scenario Legal_Article PrivacyTrainingProgram PolicyVersion RiskManagement DataFlow_Detail RetentionSchedule Jurisdiction_Mechanism_Map Control_Scenario_Map Dataset_Legal_Map TrainingMaterial EmployeeCertification GovernanceDecision PolicyAcknowledgment RiskManagement_Detail DataProfile DisposalRecord Retention_Dataset_Map TrainingCompletionLog DataProfile_Lineage SecurityProfile VendorManagement SecurityProfile_CipherDetail API_Endpoint Vendor_Contract_Detail Compliance SubprocessorRegistry API_Control_Map DPIARecord IncidentRegister DataSubjectRequest AuditAndCompliance Compliance_Detail Subprocessor_Vendor_Map DueDiligenceAssessment SLAMonitoring DPIA_Dataset_Map DPIAAssessmentCriteria DPIAStakeholderConsultation DPIARecommendation RemediationAction IncidentResponsePlan ForensicInvestigation IncidentNotification Incident_Control_Map PortabilityRequest ErasureRequest Rights_Compliance_Map ConsentRecord"
    ["planets_data_large_template"]="stars research_programs instruments_surveys astronomical_catalogs discovery_teams SpaceMission DataReductionPipeline ObservatoryWeatherLog NearbyStarSurvey SpectralLineMeasurement multi_planet_system_dynamics planets binary_star_systems stellar_spectroscopy ProperMotionCatalog ChemicalAbundanceAnalysis photometric_variations stellar_evolution_phases radial_velocity_measurements ScientificPublication ObservationProposal instrument_specifications SpectralCalibration TelescopeAllocation star_catalog_entries MissionInstrument Pipeline_Instrument_Map PipelineQualityMetric CalibrationRecord Neighborhood_Catalog_Map EmissionAbsorptionFeature Spectral_Instrument_Map atmospheric_escape_rates data_quality_tracking physical_properties PlanetCharacterizationSummary planetary_formation_models gravitational_microlensing_events TransitLightCurve planet_instrument_observations Mission_Planet_Map planetary_atmospheres tidal_forces_effects exomoons planet_discovery_teams orbital_characteristics TransmissionSpectrum planet_research_programs MissionTarget habitability_metrics planet_system_membership StellarMultiplicityRecord CitationRecord Dataset_Publication_Map Observer_Team_Map ScheduledObservation MissionDataProduct observation_conditions"
    ["sports_events_large_template"]="circuits sponsor_entities media_assets technical_regulations constructors drivers innovation_technologies staff_directory training_programs RegulatoryComplianceLog races TracksideMedicalFacility circuit_aliases circuit_details circuit_facilities sponsor_media_campaigns SensorConfiguration TeamBudget constructor_profiles SafetyEquipmentInspection CarDevelopmentProgram EquipmentShipment RevenueStream driver_social_media driver_profiles driver_biometric_metrics DriverMedicalRecord sponsor_technology_agreements regulation_technology_links staff_training_enrollments weather_observations CarTelemetrySnapshot Fan_Race_Attendance TVBroadcast sprint_results qualifying strategy_scenarios constructor_results constructor_standings driver_standings lap_times MerchandiseSales race_incidents TicketSales FanZoneActivity TeamTravelItinerary pit_stops Financial_Sponsor_Map CostCapTracking Development_Technology_Map CFDSimulation WindTunnelResult FreightContainer Logistics_Circuit_Map TelemetryAnomalyLog TireTelemetry EngineTelemetry Broadcast_Media_Map StreamingMetrics Medical_Incident_Map"
)

############################
# 2. Create template DBs and import data
############################
for DB_TEMPLATE in "${!DATABASE_MAPPING[@]}"; do
    echo "Creating template database: $DB_TEMPLATE"
    psql -U root -tc "SELECT 1 FROM pg_database WHERE datname='${DB_TEMPLATE}'" | grep -q 1 \
      || psql -U root -c "CREATE DATABASE ${DB_TEMPLATE} WITH OWNER=root ENCODING='UTF8' TEMPLATE=template0;"
done

# Function to import files from database-specific folders
import_db_files() {
    local db_template="$1"
    local db_folder="/docker-entrypoint-initdb.d/postgre_table_dumps/${db_template}"

    # check if db_folder does not exist, report error and exit
    if [[ ! -d "${db_folder}" ]]; then
        echo "Error: Folder ${db_folder} does not exist"
        exit 1
    fi
    
    echo "Importing files for ${db_template} from ${db_folder}"
    
    # Check if the folder exists
    if [[ ! -d "${db_folder}" ]]; then
        echo "Warning: Folder ${db_folder} does not exist, skipping database ${db_template}"
        return
    fi
    
    # Special case for global_atlas_template
    if [[ "${db_template}" == "global_atlas_template" ]]; then
        # Check if the schema and inputs files exist
        local schema_file="${db_folder}/global_atlas-schema.sql"
        local inputs_file="${db_folder}/global_atlas-inputs.sql"
        
        if [[ -f "${schema_file}" && -f "${inputs_file}" ]]; then
            echo "Importing global_atlas schema file to ${db_template}..."
            psql -U root -d "${db_template}" -f "${schema_file}" 2>>/tmp/error.log \
                || echo "Error importing schema file for ${db_template}. Check /tmp/error.log for details."
            
            echo "Importing global_atlas data file to ${db_template}..."
            psql -U root -d "${db_template}" -f "${inputs_file}" 2>>/tmp/error.log \
                || echo "Error importing data file for ${db_template}. Check /tmp/error.log for details."
        else
            # If the special files don't exist, fall back to importing individual table files
            echo "Special global_atlas files not found, falling back to individual table imports."
            import_table_files "${db_template}" "${db_folder}"
        fi
    else
        # Regular case: import all table files in the folder
        import_table_files "${db_template}" "${db_folder}"
    fi
}

# Function to import individual table files
import_table_files() {
    local db_template="$1"
    local db_folder="$2"
    local tables="${DATABASE_MAPPING[$db_template]}"
    
    for table in $tables; do
        local sql_file="${db_folder}/${table}.sql"
        if [[ -f "$sql_file" ]]; then
            echo "Importing ${sql_file} into database ${db_template}"
            if ! psql -U root -d "${db_template}" -f "${sql_file}" 2>>/tmp/error.log; then
                echo "Error importing ${sql_file} into database ${db_template}. Check /tmp/error.log for details."
            fi
        else
            echo "Warning: SQL file ${sql_file} not found for table ${table}"
        fi
    done
}

# Import data for each database
for DB_TEMPLATE in "${!DATABASE_MAPPING[@]}"; do
    import_db_files "${DB_TEMPLATE}"
done

if [[ -s /tmp/error.log ]]; then
    echo "Errors occurred during import:"
    cat /tmp/error.log
fi

rm -f /tmp/error.log

############################
# 3. Mark these template DBs as 'datistemplate = true'
############################
echo "Marking these template databases as 'datistemplate = true'..."
for DB_TEMPLATE in "${!DATABASE_MAPPING[@]}"; do
  psql -U root -d postgres -c "UPDATE pg_database SET datistemplate = true WHERE datname = '${DB_TEMPLATE}';" || true
done

############################
# Example usage
############################
echo "All template databases created. For example, to clone 'financial_template' into 'financial':"
echo "    dropdb financial || true"
echo "    createdb financial --template=financial_template"
echo ""
echo "Done creating template DBs."

echo "Now creating real DB from each template DB..."

for DB_TEMPLATE in "${!DATABASE_MAPPING[@]}"; do
  REAL_DB="${DB_TEMPLATE%_template}"
  echo "Checking if real database '${REAL_DB}' exists..."
  EXISTS=$(psql -U root -tc "SELECT 1 FROM pg_database WHERE datname='${REAL_DB}'" | grep -c 1 || true)
  if [[ "$EXISTS" -eq 0 ]]; then
    echo "Creating real database '${REAL_DB}' from template '${DB_TEMPLATE}'"
    psql -U root -c "CREATE DATABASE ${REAL_DB} WITH OWNER=root TEMPLATE=${DB_TEMPLATE};"
  else
    echo "Database '${REAL_DB}' already exists, skipping creation."
  fi
done

echo "Done creating real DBs."