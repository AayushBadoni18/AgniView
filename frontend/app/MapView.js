"use client";

import { useEffect, useRef } from "react";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";


export default function MapView({ collection, onSelect }) {
  const container = useRef(null);
  const map = useRef(null);
  const collectionRef = useRef(collection);
  const onSelectRef = useRef(onSelect);
  const token = process.env.NEXT_PUBLIC_MAPBOX_TOKEN;
  collectionRef.current = collection;
  onSelectRef.current = onSelect;

  useEffect(() => {
    if (!token || map.current) return;
    mapboxgl.accessToken = token;
    map.current = new mapboxgl.Map({ container: container.current, style: "mapbox://styles/mapbox/dark-v11", center: [78.2, 20.5], zoom: 4 });
    map.current.addControl(new mapboxgl.NavigationControl(), "top-left");
    map.current.on("load", () => {
      map.current.addSource("events", { type: "geojson", data: collectionRef.current, cluster: true, clusterRadius: 45 });
      map.current.addLayer({ id: "clusters", type: "circle", source: "events", filter: ["has", "point_count"], paint: { "circle-color": "#e8b44f", "circle-radius": ["step", ["get", "point_count"], 18, 20, 24, 100, 30] } });
      map.current.addLayer({ id: "events", type: "circle", source: "events", filter: ["!", ["has", "point_count"]], paint: { "circle-radius": 8, "circle-stroke-width": 2, "circle-stroke-color": "#f7f4ec", "circle-color": ["match", ["get", "classification"], "wildfire", "#e65335", "industrial", "#e8b44f", "#78a6a3"] } });
      map.current.on("click", "events", (click) => onSelectRef.current(click.features[0].properties.id));
      map.current.on("click", "clusters", async (click) => {
        const feature = map.current.queryRenderedFeatures(click.point, { layers: ["clusters"] })[0];
        const zoom = await map.current.getSource("events").getClusterExpansionZoom(feature.properties.cluster_id);
        map.current.easeTo({ center: feature.geometry.coordinates, zoom });
      });
    });
    return () => { map.current?.remove(); map.current = null; };
  }, [token]);

  useEffect(() => {
    const source = map.current?.getSource("events");
    if (source) source.setData(collection);
  }, [collection]);

  if (!token) return <div className="map-fallback"><p>Mapbox token unavailable. Event list remains interactive.</p>{collection.features.map(({ properties }) => <button key={properties.id} onClick={() => onSelect(properties.id)}><span className={`dot ${properties.classification}`} />{properties.classification} · {properties.frp ?? "—"} MW</button>)}</div>;
  return <div ref={container} className="map" aria-label="Interactive thermal event map" />;
}
