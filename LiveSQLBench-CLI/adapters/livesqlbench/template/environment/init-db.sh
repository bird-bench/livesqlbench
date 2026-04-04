#!/bin/bash
set -euo pipefail

SELECTED_DB_FILE="/docker-entrypoint-initdb.d/db_assets/db_name.txt"
DB_DUMP_DIR="/docker-entrypoint-initdb.d/db_assets/db_dump"
PREPROCESS_SQL_FILE="/docker-entrypoint-initdb.d/db_assets/preprocess.sql"

declare -A DATABASE_MAPPING=(
    ["archeology_scan_template"]="projects personnel sites equipment scans environment pointcloud mesh spatial features conservation registration processing qualitycontrol"
    ["sports_events_template"]="circuits constructors drivers races constructor_results constructor_standings driver_standings lap_times pit_stops qualifying sprint_results"
    ["cold_chain_pharma_compliance_template"]="shipments products productbatches carriers vehicles monitoringdevices environmentalmonitoring qualitycompliance incidentandriskmanagement insuranceclaims reviewsandimprovements shipsensorlink"
    ["cross_border_template"]="DataFlow RiskManagement DataProfile SecurityProfile VendorManagement Compliance AuditAndCompliance"
    ["crypto_exchange_template"]="users orders orderExecutions fees marketdata marketstats analyticsindicators riskandmargin accountbalances systemmonitoring Exchange_OrderType_Map"
    ["cybermarket_pattern_template"]="markets vendors buyers products transactions transaction_products vendor_markets vendor_countries vendor_payment_methods communications connection_security risk_analytics alerts"
    ["disaster_relief_template"]="disasterevents distributionhubs operations supplies transportation humanresources financials beneficiariesandassessments environmentandhealth coordinationandevaluation operation_hub_map"
    ["exchange_traded_funds_template"]="families exchanges categories sectors bond_ratings securities funds family_categories family_exchanges sector_allocations bond_allocations holdings performance annual_returns risk_metrics"
    ["fake_account_template"]="platforms accounts profiles security_sessions content_activity network_metrics interaction_metrics behavioral_scores risk_and_moderation cluster_analysis account_clusters monitoring"
    ["households_template"]="locations infrastructure service_types households properties transportation_assets amenities"
    ["hulushows_template"]="companies rollups core content_info availabilitys promo_info show_rollups"
    ["insider_trading_template"]="traders instruments trader_relationships order_status_types trade_records market_conditions order_behaviour manipulation_signals sentiment_analytics corporate_events reg_compliance enforcement_actions"
    ["labor_certification_applications_template"]="employer employer_poc attorney preparer worksite prevailing_wage cases case_attorney case_worksite"
    ["mental_health_template"]="facilities clinicians patients assessmentbasics encounters assessmentsymptomsandrisk assessmentsocialanddiagnosis treatmentbasics treatmentoutcomes"
    ["museum_artifact_template"]="ArtifactsCore ArtifactRatings SensitivityData ExhibitionHalls Showcases EnvironmentalReadingsCore AirQualityReadings SurfaceAndPhysicalReadings LightAndRadiationReadings ConditionAssessments RiskAssessments ConservationAndMaintenance UsageRecords ArtifactSecurityAccess Monitor_Showcase_Map"
    ["organ_transplant_template"]="demographics recipients_demographics medical_history hla_info function_and_recovery clinical recipients_immunology transplant_matching compatibility_metrics risk_evaluation allocation_details logistics administrative_and_review data_source_and_quality"
    ["planets_data_template"]="stars instruments_surveys planets orbital_characteristics physical_properties planet_instrument_observations data_quality_tracking"
    ["polar_equipment_template"]="EquipmentType Equipment Location OperationMaintenance PowerBattery EngineAndFluids Transmission ChassisAndVehicle Communication CabinEnvironment LightingAndSafety WaterAndWaste Scientific WeatherAndStructure ThermalSolarWindAndGrid StationEquipmentType"
    ["reverse_logistics_template"]="customers products orders returns quality_assessment return_processing financial_management case_management"
    ["robot_fault_prediction_template"]="robot_record robot_details operation joint_performance joint_condition actuation_data mechanical_status system_controller maintenance_and_fault performance_and_safety"
    ["solar_panel_template"]="panel_models plants plant_panel_model plant_record electrical_performance environmental_conditions mechanical_condition operational_metrics inspection alert"
    ["virtual_idol_template"]="fans virtualidols interactions membershipandspending engagement commerceandcollection socialcommunity eventsandclub loyaltyandachievements preferencesandsettings moderationandcompliance supportandfeedback retentionandinfluence additionalnotes"
    ["archeology_template"]="projects personnel sites equipment scans scanenvironment scanpointcloud scanmesh scanspatial scanfeatures scanconservation scanregistration scanprocessing scanqc"
    ["alien_template"]="observatories telescopes signals signalprobabilities signaladvancedphenomena signalclassification signaldecoding signaldynamics researchprocess observationalconditions sourceproperties"
    ["cross_db_template"]="dataflow riskmanagement dataprofile securityprofile vendormanagement compliance auditandcompliance"
    ["vaccine_template"]="shipments container transportinfo vaccinedetails regulatoryandmaintenance sensordata datalogger"
    ["gaming_template"]="testsessions performance deviceidentity mechanical audioandmedia rgb physicaldurability interactionandcontrol"
    ["museum_template"]="artifactscore artifactratings sensitivitydata exhibitionhalls showcases environmentalreadingscore airqualityreadings surfaceandphysicalreadings lightandradiationreadings conditionassessments riskassessments conservationandmaintenance usagerecords artifactsecurityaccess"
    ["polar_template"]="equipment location operationmaintenance powerbattery engineandfluids transmission chassisandvehicle communication cabinenvironment lightingandsafety waterandwaste scientific weatherandstructure thermalsolarwindandgrid"
    ["solar_template"]="plant panel performance electrical environment maintenance inverter alerts"
    ["robot_template"]="robot_record robot_details operation joint_performance joint_condition actuation_data mechanical_status system_controller maintenance_and_fault performance_and_safety"
    ["virtual_template"]="fans virtualidols interactions membershipandspending engagement commerceandcollection socialcommunity eventsandclub loyaltyandachievements moderationandcompliance preferencesandsettings supportandfeedback retentionandinfluence additionalnotes"
    ["mental_template"]="facilities clinicians patients assessmentbasics encounters assessmentsymptomsandrisk assessmentsocialanddiagnosis treatmentbasics treatmentoutcomes"
    ["news_template"]="users devices articles recommendations sessions systemperformance interactions interactionmetrics"   
    ["insider_template"]="trader transactionrecord advancedbehavior sentimentandfundamentals compliancecase investigationdetails enforcementactions"
    ["crypto_template"]="users orders orderexecutions fees marketdata marketstats analyticsindicators riskandmargin accountbalances systemmonitoring"
    ["fake_template"]="account profile sessionbehavior networkmetrics contentbehavior messaginganalysis technicalinfo securitydetection moderationaction"
    ["cybermarket_template"]="markets vendors buyers products transactions communication riskanalysis securitymonitoring investigation"
    ["credit_template"]="core_record employment_and_income expenses_and_assets bank_and_transactions credit_and_compliance credit_accounts_and_history"
    ["disaster_template"]="disasterevents distributionhubs operations supplies transportation humanresources financials beneficiariesandassessments environmentandhealth coordinationandevaluation"
)

read_selected_database() {
    echo "[init-db.sh] Checking for database name..." >&2

    if [[ ! -f "$SELECTED_DB_FILE" ]]; then
        echo "[init-db.sh] ERROR: Missing database name file: $SELECTED_DB_FILE" >&2
        exit 1
    fi

    local selected_database
    selected_database="$(tr -d '[:space:]' < "$SELECTED_DB_FILE")"

    if [[ -z "$selected_database" ]]; then
        echo "[init-db.sh] ERROR: Database name is empty" >&2
        exit 1
    fi

    if [[ ! "$selected_database" =~ ^[a-zA-Z_][a-zA-Z0-9_]*$ ]]; then
        echo "[init-db.sh] ERROR: Invalid database name: $selected_database" >&2
        exit 1
    fi

    printf '%s\n' "$selected_database"
}

import_dump_into_database() {
    local target_db="$1"

    local source_dir="$DB_DUMP_DIR"
    if [[ -L "$DB_DUMP_DIR" ]]; then
        source_dir=$(readlink -f "$DB_DUMP_DIR")
        echo "[init-db.sh] Using db_dump symlink: $source_dir"
    elif [[ -d "$DB_DUMP_DIR" ]]; then
        echo "[init-db.sh] Using db_dump directory: $source_dir"
    fi

    if [[ ! -d "$source_dir" ]]; then
        echo "[init-db.sh] ERROR: Missing db dump directory: $source_dir" >&2
        exit 1
    fi

    echo "[init-db.sh] Importing SQL dumps into $target_db from: $source_dir"
    : > /tmp/init-db-errors.log
    shopt -s nullglob

    local full_dumps=("$source_dir"/*_full.sql)
    if (( ${#full_dumps[@]} > 0 )); then
        for dump_file in "${full_dumps[@]}"; do
            echo "[init-db.sh] Restoring full dump: $(basename "$dump_file")"
            psql -v ON_ERROR_STOP=1 \
                --username "$POSTGRES_USER" \
                --dbname "$target_db" \
                -f "$dump_file" \
                2>>/tmp/init-db-errors.log
        done
        return
    fi

    local all_dumps=("$source_dir"/*.sql)
    if (( ${#all_dumps[@]} == 0 )); then
        echo "[init-db.sh] ERROR: No SQL dumps found in: $source_dir" >&2
        exit 1
    fi

    local mapped_tables_string="${DATABASE_MAPPING[$target_db]:-}"
    if [[ -n "$mapped_tables_string" ]]; then
        echo "[init-db.sh] Using DATABASE_MAPPING for restore order: $target_db"

        local ordered_tables=()
        mapfile -t ordered_tables < <(printf '%s\n' "$mapped_tables_string" | tr '[:space:]' '\n' | sed '/^$/d')

        if (( ${#ordered_tables[@]} == 0 )); then
            echo "[init-db.sh] ERROR: DATABASE_MAPPING entry for $target_db is empty after parsing" >&2
            exit 1
        fi

        echo "[init-db.sh] Ordered restore sequence:"
        printf '  - %s\n' "${ordered_tables[@]}"

        local table_name
        local dump_file
        for table_name in "${ordered_tables[@]}"; do
            dump_file="$source_dir/${table_name}.sql"

            if [[ ! -f "$dump_file" ]]; then
                echo "[init-db.sh] WARNING: Mapped dump file not found, skipping: $dump_file"
                continue
            fi

            echo "[init-db.sh] Restoring table dump: $(basename "$dump_file")"
            psql -v ON_ERROR_STOP=1 \
                --username "$POSTGRES_USER" \
                --dbname "$target_db" \
                -f "$dump_file" \
                2>>/tmp/init-db-errors.log
        done

        echo "[init-db.sh] Skipping unmapped dump files in $source_dir"
        local mapped_lookup=" $mapped_tables_string "
        for dump_file in "${all_dumps[@]}"; do
            local base table_from_file
            base="$(basename "$dump_file")"
            table_from_file="${base%.sql}"

            if [[ " $mapped_lookup " == *" $table_from_file "* ]]; then
                continue
            fi

            echo "[init-db.sh] WARNING: Dump file not listed in DATABASE_MAPPING for $target_db, skipping: $base"
        done

        return
    fi

    echo "[init-db.sh] No DATABASE_MAPPING found for $target_db; restoring in alphabetical order"
    for dump_file in "${all_dumps[@]}"; do
        echo "[init-db.sh] Restoring table dump: $(basename "$dump_file")"
        psql -v ON_ERROR_STOP=1 \
            --username "$POSTGRES_USER" \
            --dbname "$target_db" \
            -f "$dump_file" \
            2>>/tmp/init-db-errors.log
    done
}

create_template_database() {
    local selected_database="$1"
    local template_database="${selected_database}_template"

    echo "[init-db.sh] Creating template database: $template_database"
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres <<EOSQL
DROP DATABASE IF EXISTS "$template_database";
CREATE DATABASE "$template_database";
EOSQL

    import_dump_into_database "$template_database"
    echo "[init-db.sh] Template database ready: $template_database"
}

clone_template_to_agent_database() {
    local selected_database="$1"
    local template_database="${selected_database}_template"

    echo "[init-db.sh] Cloning $template_database -> $selected_database"
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres <<EOSQL
DROP DATABASE IF EXISTS "$selected_database";
CREATE DATABASE "$selected_database" WITH TEMPLATE "$template_database";
EOSQL

    echo "[init-db.sh] Agent database ready: $selected_database"
}

execute_preprocess_sqls() {
    local selected_database="$1"

    echo "[init-db.sh] Checking for preprocess SQL..."

    if [[ ! -f "$PREPROCESS_SQL_FILE" ]]; then
        echo "[init-db.sh] No preprocess SQL file found; skipping"
        return
    fi

    if [[ ! -s "$PREPROCESS_SQL_FILE" ]]; then
        echo "[init-db.sh] Preprocess SQL file is empty; skipping"
        return
    fi

    local sql_content
    sql_content=$(grep -v '^\s*--' "$PREPROCESS_SQL_FILE" | grep -v '^\s*$' || true)

    if [[ -z "$sql_content" ]]; then
        echo "[init-db.sh] Preprocess SQL file contains only comments; skipping"
        return
    fi

    echo "[init-db.sh] Executing preprocess SQL on $selected_database from: $PREPROCESS_SQL_FILE"
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$selected_database" -f "$PREPROCESS_SQL_FILE"
    echo "[init-db.sh] ✓ Preprocess SQL executed successfully"
}

SELECTED_DATABASE="$(read_selected_database)"

echo "[init-db.sh] Initializing databases for: $SELECTED_DATABASE"
create_template_database "$SELECTED_DATABASE"
clone_template_to_agent_database "$SELECTED_DATABASE"
execute_preprocess_sqls "$SELECTED_DATABASE"

echo "[init-db.sh] Database initialization finished: $SELECTED_DATABASE"