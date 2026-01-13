# Treatment History Table Structure

## Current Prescription Form Fields

The prescription form collects the following details:

1. **Diagnosis** (optional) - Text area for medical diagnosis
2. **Prescription** (required) - Text area for prescription details/medications
3. **Send to NGO** (optional) - Dropdown to select NGO to notify

## Treatment History Table Schema

The `treatment_history` table stores all prescription details:

```sql
CREATE TABLE treatment_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    appointment_id TEXT REFERENCES appointments(id) ON DELETE SET NULL,
    patient_id UUID REFERENCES patients(id) ON DELETE SET NULL,
    ngo_id UUID REFERENCES users(id) ON DELETE SET NULL,
    diagnosis TEXT,              -- Stores diagnosis from form
    prescription TEXT,           -- Stores prescription details from form
    notes TEXT,                 -- Additional notes (currently not in form, but supported)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Field Mapping

| Form Field | Table Column | Required | Description |
|------------|--------------|----------|-------------|
| Diagnosis | `diagnosis` | No | Medical diagnosis entered by doctor |
| Prescription | `prescription` | Yes | Prescription details/medications |
| Send to NGO | `ngo_id` | No | NGO to notify about prescription |
| - | `appointment_id` | Auto | Linked appointment ID |
| - | `patient_id` | Auto | Patient ID from appointment |
| - | `notes` | No | Additional notes (not in form yet) |
| - | `created_at` | Auto | Timestamp when prescription was created |

## Current Implementation Status

✅ **All form fields are being stored correctly:**
- Diagnosis → `diagnosis` column
- Prescription → `prescription` column  
- NGO selection → `ngo_id` column
- Appointment ID → `appointment_id` (auto from appointment)
- Patient ID → `patient_id` (auto from appointment)

✅ **Backend code properly maps all fields:**
- Form data is received and validated
- All fields are inserted into treatment_history table
- RPC function supports all fields

## Verification

To verify the table structure matches the form:

1. Check that all form fields have corresponding columns
2. Ensure backend code maps form data to table columns
3. Verify data is being saved correctly

All fields from the prescription form are currently being stored in the treatment_history table.
