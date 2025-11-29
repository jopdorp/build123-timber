# Timber Frame Integration Plan

A high-level guide for folding the new FEA (`fea_pipeline.py`) and COMPAS (`compas_pipeline_example.py`) pipelines into a coherent timber-frame workflow that starts with beams and ends with BIM/robotics deliverables.

---

## 1. Vision & Guiding Principles
- **Single Source of Truth**: `Beam`, `Joint`, and `Assembly` objects should own geometry, metadata, and physical properties.
- **Layered Pipelines**: Separate parametric modeling (build123d) from analysis/robotics exporters via clean adapters.
- **Composable Frames**: Posts, beams, girts, rafters, studs, pegs, and wedges should derive from the same primitives and alignment helpers.
- **Analysis-Ready by Construction**: Every assembly should be able to emit (a) FEA mesh, (b) IFC, (c) COMPAS geometry without manual surgery.

---

## 2. Current Building Blocks
| Layer | Assets | Gaps |
| --- | --- | --- |
| **Parametric Geometry** | `Beam`, `Tenon`, `alignment.py`, joint modules | Need two-sided joints, better alignment DSL |
| **Analysis** | `fea_pipeline.py` (gmsh → CalculiX → OCP), FRD parser, IFC exporter | No direct hook from assemblies to pipeline |
| **Robotics / COMPAS** | `compas_pipeline_example.py` | Needs backend plugin strategy, decoupled geometry feeds |
| **Visualization** | ocp_vscode integration, matplotlib fallback | Should support per-component styling and envelopes |

---

## 3. Proposed Architecture Layers
1. **Core Geometry Layer**
   - Data classes for `Beam`, `Post`, `Girt`, `Rafter`, `Stud`, `Peg`, `Wedge` sharing base mixins.
   - `JointDefinition` objects describing male/female interfaces, adjustable offsets, and tolerance metadata.
2. **Assembly Layer**
   - `FrameAssembly` built from `ElementPlacement` records (`element`, `location`, `alignment_rule`).
   - Automatic creation of mortise/tenon pairings when two beams meet.
3. **Export/Analysis Adapters**
   - **FEA Adapter**: Converts assembly to `fea_pipeline` input (mesh density, load cases, material map).
   - **BIM Adapter**: IFC export with spatial hierarchy (Site → Building → Storey → Frame).
   - **Robotics Adapter**: COMPAS geometry + attributes for tool paths / robot cell planning.

---

## 4. Work Breakdown Structure

### 4.1 Geometry & Joint Enhancements
- [ ] Extend `alignment.py` with declarative rules (`AlignAxis`, `FacePair`, `MortiseAt(bevel=...)`).
- [ ] Implement two-sided joint utilities:
  - `create_double_tenon(beam_a, beam_b, offset)`
  - `mirror_joint_across_face()` helper.
- [ ] Introduce `JointLibrary` catalog (butt, dovetail, half-lap, shouldered tenon) with parameter presets.
- [ ] Add metadata tags (e.g., `load_path`, `role="girt"`).

### 4.2 Frame Assembly API
- [ ] Define `ElementRole` enum (POST, BEAM, GIRT, RAFTER, STUD, BRACE, PEG, WEDGE).
- [ ] Create `TimberFrame` class with:
  - `add_element(role, element, location, alignment_rule)`
  - `auto_join(neighbors, joint_type)`
  - `validate_clearances()` returning collisions/tolerance issues.
- [ ] Provide recipe templates: `BarnFrame`, `HouseFrame`, `PortalFrame` returning populated assemblies.

### 4.3 Analysis Integration
- [ ] Assembly → FEA adapter steps:
  1. Fuse solids for load paths or keep parts separate via contact definitions.
  2. Export STEP for gmsh; attach element-set names (`TIMBER_role`) for materials.
  3. Generate load/boundary conditions from assembly metadata (e.g., posts fixed at base, rafters loaded in Z).
- [ ] Extend `fea_pipeline.py` to accept `AssemblyAnalysisConfig` (mesh size, scale factor, load cases).
- [ ] Persist solver artifacts per assembly (`analysis/{assembly_name}/...`).

### 4.4 BIM / IFC Enhancements
- [ ] Map `ElementRole` → IFC classes (`IfcColumn`, `IfcBeam`, `IfcMember`).
- [ ] Support per-element placements, material layers, custom properties (grade, moisture, joinery).
- [ ] Generate `IfcRelConnectsElements` to describe joints.
- [ ] Output schedules (beam list, peg count) for fabrication.

### 4.5 Robotics / COMPAS Path
- [ ] Refactor `compas_pipeline_example.py` into `robotics_pipeline.py` using the new adapter signature.
- [ ] Decide backend strategy (OpenSees, Abaqus plugin) for future structural validation if needed.
- [ ] Prepare toolpath placeholders (tenon cutting, drilling) feeding COMPAS_FAB / OCC.

### 4.6 Visualization Layer
- [ ] OCP scene graph builder that colors by role (posts=oak, beams=cedar, etc.).
- [ ] Optional deformation overlays from CalculiX results (already prototyped).
- [ ] Rendering presets (assembly overview, joint close-up, stress map).

---

## 5. Milestones
1. **M1 – Geometry Foundations** (weeks 1–2)
   - Alignment DSL, two-sided joints, role tagging.
2. **M2 – Assembly Engine** (weeks 3–4)
   - `TimberFrame` API, template assemblies, clearance checks.
3. **M3 – FEA Adapter** (weeks 5–6)
   - Assembly → gmsh/CalculiX automation, result storage, OCP overlay polishing.
4. **M4 – BIM & Robotics Outputs** (weeks 7–8)
   - IFC enhancements, COMPAS pipeline refactor, documentation.
5. **M5 – Demo Barn/House** (week 9)
   - Produce sample barn with posts, beams, girts, rafters, studs, pegs, wedges.

---

## 6. Deliverables & Documentation
- `docs/geometry_guidelines.md`: naming, alignment, joint conventions.
- `docs/analysis_pipeline.md`: how assemblies feed FEA.
- `docs/robotics_export.md`: COMPAS integration plan.
- Sample `examples/barn_frame.py` plus generated outputs (IFC, CalculiX results, OCP screenshots).

---

## 7. Open Questions
- Material library: extend beyond C24 (e.g., Douglas Fir, Glulam).
- Load case templates (wind, snow) for automatic boundary conditions.
- Contact modeling between pegs/wedges and main members in FEA.
- Strategy for multi-storey structures (stacked frames, diaphragm action).

---

This plan keeps the workflow beam-centric while layering analysis, BIM, and robotics outputs in a predictable, modular fashion.