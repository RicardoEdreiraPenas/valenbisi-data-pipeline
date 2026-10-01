SELECT 
    station_id,
    station_name,
    MAX(latitude) as latitude,
    MAX(longitude) as longitude,
    date_trunc('hour', timestamp) as hora,
    avg(available_bikes) as bicis_promedio,
    avg(available_slots) as huecos_promedio
FROM public.valenbisi_raw
GROUP BY 1, 2, 5