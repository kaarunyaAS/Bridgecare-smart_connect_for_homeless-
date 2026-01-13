# Prescription Form to Treatment History Table Mapping

## Prescription Form Fields

When filling the prescription form, the following details are collected:

1. **Diagnosis** (Optional)
   - Field: `<textarea id="diagnosis">`
   - Label: "Diagnosis"
   - Type: Text area (2 rows)

2. **Prescription** (Required - marked with red asterisk *)
   - Field: `<textarea id="prescription-text">`
   - Label: "Prescription"
   - Type: Text area (3 rows)
   - Placeholder: "Enter prescription details for the patient..."

3. **Send to NGO** (Optional)
   - Field: `<select id="prescription-ngo">`
   - Label: "Send to NGO"
   - Type: Dropdown select
   - Options: Populated dynamically from `/api/healthcare/ngos`

## Treatment History Table Structure

The `treatment_history` table is designed to store ALL prescription form details:

```sql
CREATE TABLE treatment_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    appointment_id TEXT REFERENCES appointments(id) ON DELETE SET NULL,  -- Auto-filled from appointment
    patient_id UUID REFERENCES patients(id) ON DELETE SET NULL,           -- Auto-filled from appointment
    ngo_id UUID REFERENCES users(id) ON DELETE SET NULL,                  -- From "Send to NGO" dropdown
    diagnosis TEXT,                                                       -- From "Diagnosis" textarea
    prescription TEXT,                                                    -- From "Prescription" textarea (required)
    notes TEXT,                                                           -- Additional notes (not in form, but supported)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP                       -- Auto-generated timestamp
);
```

## Data Flow: Form → Backend → Database

### 1. Form Submission (Frontend)
```javascript
// Form collects:
const diagnosis = document.getElementById('diagnosis').value.trim();
const prescriptionText = document.getElementById('prescription-text').value.trim();
const ngoId = document.getElementById('prescription-ngo').value || null;

// Sends to backend:
const payload = { 
    diagnosis: diagnosis, 
    prescription: prescriptionText, 
    ngo_id: ngoId 
};
```

### 2. Backend Processing
```python
# Receives form data:
diagnosis = data.get('diagnosis')           # From form
prescription = data.get('prescription')      # From form (required)
ngo_id = data.get('ngo_id')                 # From form

# Gets from appointment:
appointment_id = appointment_id              # From URL parameter
patient_id = ap.get('patient_id')           # From appointment record
target_ngo = ngo_id or ap.get('ngo_id')     # Form value or appointment's ngo_id

# Builds insert payload:
th = {
    'appointment_id': appointment_id,          # Auto
    'patient_id': patient_id,               # Auto
    'prescription': prescription,           # From form ✓
    'ngo_id': target_ngo,                  # From form ✓
    'diagnosis': diagnosis,                 # From form ✓
    'notes': data.get('notes')              # Optional (not in form)
}
```

### 3. Database Storage
All fields are inserted into `treatment_history` table via:
- RPC function: `insert_treatment_history()` (preferred - bypasses schema cache)
- Direct insert: `supabase.table('treatment_history').insert(th)` (fallback)

## Field Mapping Summary

| Form Field | Form ID | Backend Variable | Table Column | Status |
|------------|---------|------------------|--------------|--------|
| Diagnosis | `diagnosis` | `diagnosis` | `diagnosis` | ✅ Stored |
| Prescription | `prescription-text` | `prescription` | `prescription` | ✅ Stored (Required) |
| Send to NGO | `prescription-ngo` | `ngo_id` | `ngo_id` | ✅ Stored |
| Appointment ID | - | `appointment_id` | `appointment_id` | ✅ Auto-filled |
| Patient ID | - | `patient_id` | `patient_id` | ✅ Auto-filled |
| Notes | - | `notes` | `notes` | ⚠️ Supported but not in form |
| Created At | - | - | `created_at` | ✅ Auto-generated |

## Verification Checklist

✅ **Form fields match table columns:**
- Diagnosis → `diagnosis` column
- Prescription → `prescription` column
- NGO selection → `ngo_id` column

✅ **Auto-filled fields:**
- Appointment ID is automatically linked
- Patient ID is automatically linked from appointment
- Created timestamp is automatically generated

✅ **Backend code properly handles:**
- All form fields are received
- All fields are validated
- All fields are stored in database
- RPC function supports all fields

## Conclusion

**The treatment_history table structure is correctly designed to store all prescription form details.** All fields collected in the form are being properly stored in the database table.
