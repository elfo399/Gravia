import { ChevronDown } from 'lucide-react';
import { useGraviaData } from '../hooks/useGraviaData';
import { isActivityActive } from '../types/ActivitySession';
import { activeStatuses } from '../types/MeasurementSession';
export function ProfileSelector() {
  const { profiles, profile, profileId, selectProfile, live } = useGraviaData();
  return (
    <div className="profile-selector">
      <span className="avatar">{profile?.name.charAt(0).toUpperCase() || '?'}</span>
      <label>
        <span>Profilo attivo</span>
        <select
          aria-label="Profilo attivo"
          value={profileId}
          disabled={
            isActivityActive(live.activityStatus?.status) ||
            (!!live.sessionEvent && activeStatuses.includes(live.sessionEvent.status))
          }
          onChange={(event) => selectProfile(event.target.value)}
        >
          {!profiles.length && <option value="">Nessun profilo</option>}
          {profiles.map((profile) => (
            <option key={profile.id} value={profile.id}>
              {profile.name}
            </option>
          ))}
        </select>
      </label>
      <ChevronDown size={16} />
    </div>
  );
}
