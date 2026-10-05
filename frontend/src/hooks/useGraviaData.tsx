import { createContext, type ReactNode, useCallback, useContext, useEffect, useState } from 'react';
import { measurementsApi } from '../api/measurementsApi';
import { profilesApi } from '../api/profilesApi';
import type { Measurement } from '../types/Measurement';
import type { Profile } from '../types/Profile';
import { useLiveMeasurement } from './useLiveMeasurement';

interface GraviaData {
  profiles: Profile[];
  measurements: Measurement[];
  profile: Profile | undefined;
  profileId: string;
  selectProfile: (id: string) => void;
  refresh: () => Promise<void>;
  loading: boolean;
  error: string;
  live: ReturnType<typeof useLiveMeasurement>;
}
const GraviaContext = createContext<GraviaData | null>(null);
export function GraviaDataProvider({ children }: { children: ReactNode }) {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [measurements, setMeasurements] = useState<Measurement[]>([]);
  const [profileId, setProfileId] = useState(localStorage.getItem('gravia.profileId') || '');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const live = useLiveMeasurement();
  const refresh = useCallback(async () => {
    try {
      const [people, readings] = await Promise.all([profilesApi.list(), measurementsApi.list()]);
      setProfiles(people);
      setMeasurements(readings);
      setError('');
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Impossibile caricare i dati.');
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => {
    void refresh();
  }, [refresh]);
  useEffect(() => {
    if (live.connected) void refresh();
  }, [refresh, live.connected]);
  useEffect(() => {
    if (live.completed?.id) void refresh();
  }, [live.completed?.id, refresh]);
  useEffect(() => {
    if (profiles.length && !profiles.some((profile) => profile.id === profileId))
      setProfileId(profiles[0].id);
  }, [profiles, profileId]);
  useEffect(() => {
    localStorage.setItem('gravia.profileId', profileId);
  }, [profileId]);
  return (
    <GraviaContext.Provider
      value={{
        profiles,
        measurements,
        profileId,
        selectProfile: setProfileId,
        profile: profiles.find((profile) => profile.id === profileId),
        refresh,
        loading,
        error,
        live,
      }}
    >
      {children}
    </GraviaContext.Provider>
  );
}
export function useGraviaData() {
  const data = useContext(GraviaContext);
  if (!data) throw new Error('GraviaDataProvider is required');
  return data;
}
