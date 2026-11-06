-- Allow 'month' as a rate unit for contacts.standard rate and crew job rate.
ALTER TABLE contacts DROP CONSTRAINT IF EXISTS contacts_rate_unit_check;
ALTER TABLE contacts ADD CONSTRAINT contacts_rate_unit_check
    CHECK (rate_unit IS NULL OR rate_unit IN ('day','week','month','flat'));

ALTER TABLE production_crew DROP CONSTRAINT IF EXISTS production_crew_job_rate_unit_check;
ALTER TABLE production_crew ADD CONSTRAINT production_crew_job_rate_unit_check
    CHECK (job_rate_unit IS NULL OR job_rate_unit IN ('day','week','month','flat'));
