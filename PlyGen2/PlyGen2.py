# Author-
# Description-PlyGen2: Fixed joinery issues using working code from PlywoodPanelGen.

import adsk.core, adsk.fusion, adsk.cam, traceback, math

_handlers = []

CMD_ID = 'plygen2_v1'
CMD_NAME = 'PlyGen2'
CMD_Description = 'Parametric plywood frame with Fixed Joinery.'

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui  = app.userInterface

        cmdDefs = ui.commandDefinitions
        cmdDef = cmdDefs.itemById(CMD_ID)
        if cmdDef:
            cmdDef.deleteMe()
            
        cmdDef = cmdDefs.addButtonDefinition(CMD_ID, CMD_NAME, CMD_Description, '')

        onCommandCreated = PanelCommandCreatedHandler()
        cmdDef.commandCreated.add(onCommandCreated)
        _handlers.append(onCommandCreated)

        workspaces = ui.workspaces
        modelingWorkspace = workspaces.itemById('FusionSolidEnvironment')
        toolbarPanels = modelingWorkspace.toolbarPanels
        createPanel = toolbarPanels.itemById('SolidCreatePanel')
        
        buttonControl = createPanel.controls.addCommand(cmdDef)
        buttonControl.isPromoted = True

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

def stop(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui  = app.userInterface

        cmdDef = ui.commandDefinitions.itemById(CMD_ID)
        if cmdDef:
            cmdDef.deleteMe()

        workspaces = ui.workspaces
        modelingWorkspace = workspaces.itemById('FusionSolidEnvironment')
        toolbarPanels = modelingWorkspace.toolbarPanels
        createPanel = toolbarPanels.itemById('SolidCreatePanel')
        cntrl = createPanel.controls.itemById(CMD_ID)
        if cntrl:
            cntrl.deleteMe()

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


class PanelCommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            cmd = args.command
            cmd.isExecutedWhenPrecomputed = True
            inputs = cmd.commandInputs
            
            # --- GROUP 1: DIMENSIONS ---
            grp_dim = inputs.addGroupCommandInput('grp_dim', 'Panel Dimensions')
            grp_dim.isExpanded = True
            
            origin_sel = grp_dim.children.addSelectionInput('origin_select', 'Frame Origin (Optional)', 'Select Vertex or Point')
            origin_sel.addSelectionFilter('Vertices')
            origin_sel.addSelectionFilter('SketchPoints')
            origin_sel.addSelectionFilter('ConstructionPoints')
            origin_sel.setSelectionLimits(0, 1)
            
            grp_dim.children.addValueInput('height', 'Height', 'in', adsk.core.ValueInput.createByString('95 in'))
            grp_dim.children.addValueInput('width', 'Width', 'in', adsk.core.ValueInput.createByString('47 in'))
            grp_dim.children.addValueInput('depth', 'Depth', 'in', adsk.core.ValueInput.createByString('8 in'))
            grp_dim.children.addValueInput('ply', 'Ply Thickness', 'in', adsk.core.ValueInput.createByString('0.71 in'))

            # --- GROUP 2: JOINERY CONFIGURATION ---
            grp_join = inputs.addGroupCommandInput('grp_join', 'Joinery Configuration')
            grp_join.isExpanded = True
            
            grp_join.children.addIntegerSliderCommandInput('num_rails', 'Number of Middle Rails', 0, 10).valueOne = 1
            
            drop = grp_join.children.addDropDownCommandInput('joint_type', 'Middle Rail Joints', adsk.core.DropDownStyles.TextListDropDownStyle)
            drop.listItems.add('Butt Joint', True)
            drop.listItems.add('Dado (0.05")', False)
            drop.listItems.add('Mortise & Tenon', False)
            
            grp_join.children.addSeparatorCommandInput('sep1')
            
            box_chk = grp_join.children.addBoolValueInput('use_box_corners', 'Apply Box Joint Corners', True, '', False)
            fingers = grp_join.children.addIntegerSliderCommandInput('num_fingers', '   - Finger Count (Odd)', 3, 15)
            fingers.valueOne = 5
            fingers.isVisible = False 

            # --- GROUP 3: COVER PANELS ---
            grp_pan = inputs.addGroupCommandInput('grp_pan', 'Cover Panels')
            grp_pan.isExpanded = True
            
            grp_pan.children.addBoolValueInput('has_front', 'Add Front Panel', True, '', False)
            grp_pan.children.addBoolValueInput('has_back', 'Add Backing Panel', True, '', False)
            grp_pan.children.addValueInput('panel_thick', 'Panel Thickness', 'in', adsk.core.ValueInput.createByString('0.25 in'))

            # --- GROUP 4: ADVANCED SETTINGS ---
            grp_set = inputs.addGroupCommandInput('grp_set', 'Advanced Settings')
            grp_set.isExpanded = False
            
            grp_set.children.addBoolValueInput('apply_tol', 'Apply Tolerance Gap', True, '', False)
            grp_set.children.addValueInput('tol_gap', 'Gap Size', 'in', adsk.core.ValueInput.createByString('0.02 in'))

            onInputChanged = PanelInputChangedHandler()
            cmd.inputChanged.add(onInputChanged)
            _handlers.append(onInputChanged)

            onExecute = PanelCommandExecuteHandler()
            cmd.execute.add(onExecute)
            _handlers.append(onExecute)

        except:
            if adsk.core.Application.get().userInterface:
                adsk.core.Application.get().userInterface.messageBox('Failed:\n{}'.format(traceback.format_exc()))

class PanelInputChangedHandler(adsk.core.InputChangedEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            inputs = args.firingEvent.sender.commandInputs
            changedInput = args.input
            if changedInput.id == 'use_box_corners':
                finger_slider = inputs.itemById('num_fingers')
                if finger_slider:
                    finger_slider.isVisible = changedInput.value
        except:
            pass

class PanelCommandExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            app = adsk.core.Application.get()
            design = app.activeProduct
            ui = app.userInterface
            
            inputs = args.command.commandInputs
            
            height = inputs.itemById('height').value
            width = inputs.itemById('width').value
            depth = inputs.itemById('depth').value
            ply = inputs.itemById('ply').value
            num_rails = inputs.itemById('num_rails').valueOne
            joint_type = inputs.itemById('joint_type').selectedItem.name
            use_box_corners = inputs.itemById('use_box_corners').value
            num_fingers = inputs.itemById('num_fingers').valueOne
            has_back = inputs.itemById('has_back').value
            has_front = inputs.itemById('has_front').value
            panel_th = inputs.itemById('panel_thick').value
            apply_tol = inputs.itemById('apply_tol').value
            tol_gap = inputs.itemById('tol_gap').value
            
            origin_sel = inputs.itemById('origin_select')
            target_pt_world = adsk.core.Point3D.create(0,0,0)
            
            if origin_sel.selectionCount > 0:
                sel = origin_sel.selection(0)
                ent = sel.entity
                if isinstance(ent, adsk.fusion.BRepVertex) or isinstance(ent, adsk.fusion.SketchPoint):
                    if ent.nativeObject:
                        target_pt_world = ent.nativeObject.geometry
                        if ent.assemblyContext:
                            target_pt_world.transformBy(ent.assemblyContext.transform)
                    else:
                        target_pt_world = ent.geometry
                        if ent.assemblyContext:
                             target_pt_world.transformBy(ent.assemblyContext.transform)
                elif isinstance(ent, adsk.fusion.ConstructionPoint):
                    target_pt_world = ent.geometry.copy()
                    if ent.assemblyContext:
                         target_pt_world.transformBy(ent.assemblyContext.transform)
                else:
                    target_pt_world = sel.point

            # --- TRANSFORM LOGIC ---
            root_comp = design.rootComponent
            new_transform = adsk.core.Matrix3D.create()
            new_transform.translation = target_pt_world.asVector()

            # --- CREATE AT ORIGIN ---
            identity_transform = adsk.core.Matrix3D.create()
            new_occ = root_comp.occurrences.addNewComponent(identity_transform)
            new_comp = new_occ.component
            new_comp.name = "Plywood Panel Frame"

            # --- BUILD GEOMETRY ---
            new_occ.activate() 
            sketches = new_comp.sketches
            sketch = sketches.add(new_comp.xYConstructionPlane)
            lines = sketch.sketchCurves.sketchLines
            dims = sketch.sketchDimensions
            gc = sketch.geometricConstraints

            dado_depth = 0.05 * 2.54 
            rail_x_start = ply
            rail_x_end = width - ply
            if joint_type == 'Dado (0.05")':
                rail_x_start -= dado_depth
                rail_x_end += dado_depth

            # Main Frame (With Dims)
            bp_geom = self.draw_rect_with_info(sketch, 0, 0, width, ply, True, True)
            tp_geom = self.draw_rect_with_info(sketch, 0, height - ply, width, height, False, True)
            ls_geom = self.draw_rect_with_info(sketch, 0, ply, ply, height - ply, True, True)
            rs_geom = self.draw_rect_with_info(sketch, width - ply, ply, width, height - ply, True, False)

            # --- CONSTRAINTS ---
            try: gc.addCoincident(bp_geom['points'][0], sketch.originPoint)
            except: pass

            try: gc.addCollinear(ls_geom['lines'][3], bp_geom['lines'][3]); gc.addCollinear(ls_geom['lines'][3], tp_geom['lines'][3])
            except: pass
            try: gc.addCollinear(rs_geom['lines'][1], bp_geom['lines'][1]); gc.addCollinear(rs_geom['lines'][1], tp_geom['lines'][1])
            except: pass

            try: gc.addCoincident(ls_geom['points'][0], bp_geom['points'][3]); gc.addCoincident(ls_geom['points'][3], tp_geom['points'][0])
            except: pass
            try: gc.addCoincident(rs_geom['points'][1], bp_geom['points'][2]); gc.addCoincident(rs_geom['points'][2], tp_geom['points'][1])
            except: pass
            try: gc.addCollinear(rs_geom['lines'][2], tp_geom['lines'][0]); gc.addCollinear(rs_geom['lines'][1], tp_geom['lines'][1])
            except: pass

            middle_rail_y_centers = [] 
            rail_geometries = []
            if num_rails > 0:
                internal_h = height - (2 * ply)
                section_height = internal_h / (num_rails + 1)
                for i in range(1, num_rails + 1):
                    center_y = ply + (section_height * i)
                    middle_rail_y_centers.append(center_y)
                    r_geom = self.draw_rect(lines, rail_x_start, center_y - (ply/2), rail_x_end, center_y + (ply/2))
                    rail_geometries.append(r_geom)
                # Constrain and dimension middle rail lines
                for r_geom in rail_geometries:
                    try:
                        gc.addHorizontal(r_geom['lines'][0]); gc.addVertical(r_geom['lines'][1])
                        gc.addHorizontal(r_geom['lines'][2]); gc.addVertical(r_geom['lines'][3])
                    except: pass
                    try:
                        gc.addCoincident(r_geom['lines'][0].endSketchPoint, r_geom['lines'][1].startSketchPoint)
                        gc.addCoincident(r_geom['lines'][1].endSketchPoint, r_geom['lines'][2].startSketchPoint)
                        gc.addCoincident(r_geom['lines'][2].endSketchPoint, r_geom['lines'][3].startSketchPoint)
                        gc.addCoincident(r_geom['lines'][3].endSketchPoint, r_geom['lines'][0].startSketchPoint)
                    except: pass
                    try:
                        dims.addDistanceDimension(
                            r_geom['lines'][0].startSketchPoint, r_geom['lines'][0].endSketchPoint,
                            adsk.fusion.DimensionOrientations.HorizontalDimensionOrientation,
                            adsk.core.Point3D.create(width / 2, r_geom['lines'][0].startSketchPoint.geometry.y - 1, 0)
                        )
                    except: pass
                    try:
                        dims.addDistanceDimension(
                            r_geom['lines'][1].startSketchPoint, r_geom['lines'][1].endSketchPoint,
                            adsk.fusion.DimensionOrientations.VerticalDimensionOrientation,
                            adsk.core.Point3D.create(r_geom['lines'][1].startSketchPoint.geometry.x + 1, r_geom['lines'][1].startSketchPoint.geometry.y, 0)
                        )
                    except: pass
            # --- CONSTRUCTION LINES BETWEEN RAILS ---
            if num_rails > 0:
                mid_x = width / 2.0
                construction_lines = []
                
                # From center of bottom plate top line to bottom of first rail
                bp_top_center = adsk.core.Point3D.create(mid_x, ply, 0)
                first_rail_bottom = adsk.core.Point3D.create(mid_x, middle_rail_y_centers[0] - (ply/2), 0)
                cl1 = sketch.sketchCurves.sketchLines.addByTwoPoints(bp_top_center, first_rail_bottom)
                cl1.isConstruction = True
                try:
                    gc.addVertical(cl1)
                    gc.addMidPoint(cl1.startSketchPoint, bp_geom['lines'][2])  # start at midpoint of bottom plate top line
                    gc.addMidPoint(cl1.endSketchPoint, rail_geometries[0]['lines'][0])  # end at midpoint of first rail bottom line
                except: pass
                dims.addDistanceDimension(cl1.startSketchPoint, cl1.endSketchPoint, 
                                          adsk.fusion.DimensionOrientations.VerticalDimensionOrientation,
                                          adsk.core.Point3D.create(mid_x + 2, (ply + first_rail_bottom.y) / 2, 0))
                construction_lines.append(cl1)
                
                # Between rails
                for i in range(len(rail_geometries) - 1):
                    rail_top = adsk.core.Point3D.create(mid_x, middle_rail_y_centers[i] + (ply/2), 0)
                    next_rail_bottom = adsk.core.Point3D.create(mid_x, middle_rail_y_centers[i+1] - (ply/2), 0)
                    cl = sketch.sketchCurves.sketchLines.addByTwoPoints(rail_top, next_rail_bottom)
                    cl.isConstruction = True
                    try:
                        gc.addVertical(cl)
                        gc.addMidPoint(cl.startSketchPoint, rail_geometries[i]['lines'][2])  # start at midpoint of rail top line
                        gc.addMidPoint(cl.endSketchPoint, rail_geometries[i+1]['lines'][0])  # end at midpoint of next rail bottom line
                    except: pass
                    dims.addDistanceDimension(cl.startSketchPoint, cl.endSketchPoint,
                                              adsk.fusion.DimensionOrientations.VerticalDimensionOrientation,
                                              adsk.core.Point3D.create(mid_x + 2, (rail_top.y + next_rail_bottom.y) / 2, 0))
                    construction_lines.append(cl)
                
                # From top of last rail to center of top plate bottom line
                last_rail_top = adsk.core.Point3D.create(mid_x, middle_rail_y_centers[-1] + (ply/2), 0)
                tp_bottom_center = adsk.core.Point3D.create(mid_x, height - ply, 0)
                cl_last = sketch.sketchCurves.sketchLines.addByTwoPoints(last_rail_top, tp_bottom_center)
                cl_last.isConstruction = True
                try:
                    gc.addVertical(cl_last)
                    gc.addMidPoint(cl_last.startSketchPoint, rail_geometries[-1]['lines'][2])  # start at midpoint of last rail top line
                    gc.addMidPoint(cl_last.endSketchPoint, tp_geom['lines'][0])  # end at midpoint of top plate bottom line
                except: pass
                construction_lines.append(cl_last)

            # --- PROFILE SELECTION (Using simple bounding box method from working version) ---
            horiz_profs = adsk.core.ObjectCollection.create()
            vert_profs = adsk.core.ObjectCollection.create()
            tolerance = 0.01

            for prof in sketch.profiles:
                bbox = prof.boundingBox
                h = bbox.maxPoint.y - bbox.minPoint.y
                w = bbox.maxPoint.x - bbox.minPoint.x
                if abs(h - ply) < tolerance: horiz_profs.add(prof)
                elif abs(w - ply) < tolerance: vert_profs.add(prof)

            extrudes = new_comp.features.extrudeFeatures
            dist_val = adsk.core.ValueInput.createByReal(depth)
            
            stile_bodies = adsk.core.ObjectCollection.create()
            rail_bodies = adsk.core.ObjectCollection.create()

            if horiz_profs.count > 0:
                ext1 = extrudes.addSimple(horiz_profs, dist_val, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
                ext1.name = "Horizontal Parts"
                for b in ext1.bodies: 
                    # Tag bodies for tolerance analysis
                    if b.boundingBox.minPoint.y < ply * 2: b.name = "Plate"
                    elif b.boundingBox.maxPoint.y > height - ply * 2: b.name = "Plate"
                    else: b.name = "Rail"
                    rail_bodies.add(b)

            if vert_profs.count > 0:
                ext2 = extrudes.addSimple(vert_profs, dist_val, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
                ext2.name = "Vertical Stiles"
                for b in ext2.bodies: 
                    b.name = "Stile"
                    stile_bodies.add(b)

            # --- JOINERY ---
            if joint_type == 'Dado (0.05")' and rail_bodies.count > 0:
                combines = new_comp.features.combineFeatures
                for i in range(stile_bodies.count):
                    input_data = combines.createInput(stile_bodies.item(i), rail_bodies)
                    input_data.operation = adsk.fusion.FeatureOperations.CutFeatureOperation
                    input_data.isKeepToolBodies = True
                    combines.add(input_data)

            elif joint_type == 'Mortise & Tenon' and num_rails > 0:
                stile_list = [stile_bodies.item(i) for i in range(stile_bodies.count)]
                rail_list = [rail_bodies.item(i) for i in range(rail_bodies.count)]
                t_width_z = depth / 3.0
                z_min_mt = (depth / 2.0) - (t_width_z / 2.0)
                z_max_mt = (depth / 2.0) + (t_width_z / 2.0)
                t_height = ply

                def create_mt_middle(offset_x, sign):
                    planes = new_comp.constructionPlanes
                    pi = planes.createInput()
                    pi.setByOffset(new_comp.yZConstructionPlane, adsk.core.ValueInput.createByReal(offset_x))
                    cp = planes.add(pi)
                    s = sketches.add(cp)
                    sl = s.sketchCurves.sketchLines
                    s_gc = s.geometricConstraints  # Use this sketch's constraints, not the main sketch's
                    s_dims = s.sketchDimensions  # For adding dimensions
                    tenon_rects = []
                    
                    def get_rect_lines_categorized(rect_lines):
                        """Categorize rectangle lines into top, bottom, left, right"""
                        horiz = []
                        vert = []
                        for ln in rect_lines:
                            try:
                                y1 = ln.startSketchPoint.geometry.y
                                y2 = ln.endSketchPoint.geometry.y
                                z1 = ln.startSketchPoint.geometry.x  # In YZ plane, x is actually z
                                z2 = ln.endSketchPoint.geometry.x
                            except:
                                continue
                            if abs(y1 - y2) < 1e-4:  # Horizontal line (same y)
                                horiz.append(ln)
                            elif abs(z1 - z2) < 1e-4:  # Vertical line (same z)
                                vert.append(ln)
                        # Sort to get top/bottom and left/right
                        horiz.sort(key=lambda l: (l.startSketchPoint.geometry.y + l.endSketchPoint.geometry.y) / 2, reverse=True)
                        vert.sort(key=lambda l: (l.startSketchPoint.geometry.x + l.endSketchPoint.geometry.x) / 2)
                        top = horiz[0] if len(horiz) > 0 else None
                        bottom = horiz[1] if len(horiz) > 1 else None
                        left = vert[0] if len(vert) > 0 else None
                        right = vert[1] if len(vert) > 1 else None
                        return top, bottom, left, right
                    
                    for cy in middle_rail_y_centers:
                        rect_lines = self.draw_sketch_rect_3d(s, sl, offset_x, cy, t_height, z_min_mt, z_max_mt)
                        if rect_lines:
                            tenon_rects.append((cy, rect_lines))
                            # Add constraints and dimensions to this rectangle
                            top_ln, bottom_ln, left_ln, right_ln = get_rect_lines_categorized(rect_lines)
                            # Add horizontal constraints
                            if top_ln:
                                try:
                                    s_gc.addHorizontal(top_ln)
                                except:
                                    pass
                            if bottom_ln:
                                try:
                                    s_gc.addHorizontal(bottom_ln)
                                except:
                                    pass
                            # Add vertical constraints
                            if left_ln:
                                try:
                                    s_gc.addVertical(left_ln)
                                except:
                                    pass
                            if right_ln:
                                try:
                                    s_gc.addVertical(right_ln)
                                except:
                                    pass
                            # Add dimension to top horizontal line
                            if top_ln:
                                try:
                                    mid_y = (top_ln.startSketchPoint.geometry.y + top_ln.endSketchPoint.geometry.y) / 2
                                    mid_x = (top_ln.startSketchPoint.geometry.x + top_ln.endSketchPoint.geometry.x) / 2
                                    dim_pt = adsk.core.Point3D.create(mid_x, mid_y + 0.3, 0)
                                    s_dims.addDistanceDimension(top_ln.startSketchPoint, top_ln.endSketchPoint,
                                        adsk.fusion.DimensionOrientations.HorizontalDimensionOrientation, dim_pt)
                                except:
                                    pass
                            # Add dimension to left vertical line
                            if left_ln:
                                try:
                                    mid_y = (left_ln.startSketchPoint.geometry.y + left_ln.endSketchPoint.geometry.y) / 2
                                    mid_x = (left_ln.startSketchPoint.geometry.x + left_ln.endSketchPoint.geometry.x) / 2
                                    dim_pt = adsk.core.Point3D.create(mid_x - 0.3, mid_y, 0)
                                    s_dims.addDistanceDimension(left_ln.startSketchPoint, left_ln.endSketchPoint,
                                        adsk.fusion.DimensionOrientations.VerticalDimensionOrientation, dim_pt)
                                except:
                                    pass

                    # Project rail side edges and align tenon rectangles to rail projections
                    def get_horizontal_top_bottom(lines):
                        top_line = None
                        bottom_line = None
                        top_y = None
                        bottom_y = None
                        for ln in lines:
                            try:
                                y1 = ln.startSketchPoint.geometry.y
                                y2 = ln.endSketchPoint.geometry.y
                            except:
                                continue
                            if abs(y1 - y2) < 1e-4:
                                y_val = (y1 + y2) / 2.0
                                if top_y is None or y_val > top_y:
                                    top_y = y_val
                                    top_line = ln
                                if bottom_y is None or y_val < bottom_y:
                                    bottom_y = y_val
                                    bottom_line = ln
                        return top_line, bottom_line

                    projected_by_cy = []
                    for rail in rail_list:
                        # Find the rail face on this side (offset_x)
                        target_face = None
                        for f in rail.faces:
                            if f.geometry.surfaceType != adsk.core.SurfaceTypes.PlaneSurfaceType:
                                continue
                            try:
                                ret_f, param_f = f.evaluator.getParameterAtPoint(f.pointOnFace)
                                ret_f, normal_f = f.evaluator.getNormalAtParameter(param_f)
                            except:
                                continue
                            if abs(normal_f.x) < 0.9:
                                continue
                            if abs(f.pointOnFace.x - offset_x) > 0.01:
                                continue
                            target_face = f
                            break

                        if not target_face:
                            continue

                        projected = []
                        for e in target_face.edges:
                            try:
                                proj = s.project(e)
                                for c in proj:
                                    if isinstance(c, adsk.fusion.SketchLine):
                                        try:
                                            c.isConstruction = True
                                        except:
                                            pass
                                        projected.append(c)
                            except:
                                pass

                        top_line, bottom_line = get_horizontal_top_bottom(projected)
                        if top_line and bottom_line:
                            try:
                                bb = rail.boundingBox
                                rail_cy = (bb.minPoint.y + bb.maxPoint.y) / 2.0
                            except:
                                rail_cy = None
                            projected_by_cy.append((rail_cy, top_line, bottom_line))

                    # Constrain tenon rectangle top/bottom to projected rail top/bottom
                    for cy, rect_lines in tenon_rects:
                        top_tenon, bottom_tenon = get_horizontal_top_bottom(rect_lines)
                        if not top_tenon or not bottom_tenon:
                            continue
                        # Find closest projected rail by y-center
                        closest = None
                        closest_dist = None
                        for rail_cy, top_proj, bottom_proj in projected_by_cy:
                            if rail_cy is None:
                                continue
                            dist = abs(rail_cy - cy)
                            if closest_dist is None or dist < closest_dist:
                                closest_dist = dist
                                closest = (top_proj, bottom_proj)
                        if closest:
                            try:
                                s_gc.addCollinear(top_tenon, closest[0])
                            except:
                                pass
                            try:
                                s_gc.addCollinear(bottom_tenon, closest[1])
                            except:
                                pass
                            # Center the tenon on the rail using midpoint constraints
                            # Create a construction point at the geometric midpoint of tenon top line
                            try:
                                tenon_mid_x = (top_tenon.startSketchPoint.geometry.x + top_tenon.endSketchPoint.geometry.x) / 2
                                tenon_mid_y = (top_tenon.startSketchPoint.geometry.y + top_tenon.endSketchPoint.geometry.y) / 2
                                mid_pt = s.sketchPoints.add(adsk.core.Point3D.create(tenon_mid_x, tenon_mid_y, 0))
                                mid_pt.isFixed = False
                                # Constrain this point to be at the midpoint of the tenon top line
                                s_gc.addMidPoint(mid_pt, top_tenon)
                                # Constrain this same point to be at the midpoint of the projected rail top line
                                # This forces both midpoints to coincide, centering the tenon on the rail
                                s_gc.addMidPoint(mid_pt, closest[0])
                            except:
                                pass
                    if s.profiles.count > 0:
                        pc = adsk.core.ObjectCollection.create()
                        for p in s.profiles: pc.add(p)
                        dist = adsk.core.ValueInput.createByReal(ply * sign)
                        if stile_list:
                            ci = extrudes.createInput(pc, adsk.fusion.FeatureOperations.CutFeatureOperation)
                            ci.setDistanceExtent(False, dist)
                            ci.participantBodies = stile_list
                            extrudes.add(ci)
                        if rail_list:
                            ji = extrudes.createInput(pc, adsk.fusion.FeatureOperations.JoinFeatureOperation)
                            ji.setDistanceExtent(False, dist)
                            ji.participantBodies = rail_list
                            extrudes.add(ji)
                    cp.isLightBulbOn = False

                create_mt_middle(ply, -1)
                create_mt_middle(width - ply, 1)

            if use_box_corners:
                stile_list = [stile_bodies.item(i) for i in range(stile_bodies.count)]
                rail_list = [rail_bodies.item(i) for i in range(rail_bodies.count)]
                corner_y_centers = [ply/2, height - ply/2]
                t_height = ply 
                
                def create_box_corners(offset_x, sign):
                    planes = new_comp.constructionPlanes
                    pi = planes.createInput()
                    pi.setByOffset(new_comp.yZConstructionPlane, adsk.core.ValueInput.createByReal(offset_x))
                    cp = planes.add(pi)
                    s = sketches.add(cp)
                    sl = s.sketchCurves.sketchLines
                    finger_w = depth / num_fingers
                    for cy in corner_y_centers:
                        for i in range(num_fingers):
                            if i % 2 == 0:
                                z_min = i * finger_w
                                z_max = (i + 1) * finger_w
                                self.draw_sketch_rect_3d(s, sl, offset_x, cy, t_height, z_min, z_max)
                    if s.profiles.count > 0:
                        pc = adsk.core.ObjectCollection.create()
                        for p in s.profiles: pc.add(p)
                        dist = adsk.core.ValueInput.createByReal(ply * sign)
                        if stile_list:
                            ji = extrudes.createInput(pc, adsk.fusion.FeatureOperations.JoinFeatureOperation)
                            ji.setDistanceExtent(False, dist)
                            ji.participantBodies = stile_list
                            extrudes.add(ji)
                        if rail_list:
                            ci = extrudes.createInput(pc, adsk.fusion.FeatureOperations.CutFeatureOperation)
                            ci.setDistanceExtent(False, dist)
                            ci.participantBodies = rail_list
                            extrudes.add(ci)
                    cp.isLightBulbOn = False

                create_box_corners(ply, -1)
                create_box_corners(width - ply, 1)

            # --- TOLERANCE ---
            if apply_tol:
                design.activateRootComponent()
                adsk.doEvents()
                frame_bodies_proxy = []
                for b in new_occ.bRepBodies:
                    frame_bodies_proxy.append(b)
                if len(frame_bodies_proxy) >= 2:
                    cuts_needed = self.analyze_tolerance(app, frame_bodies_proxy)
                    if len(cuts_needed) > 0:
                        new_occ.activate()
                        adsk.doEvents()
                        created_feats = []
                        dist_input = adsk.core.ValueInput.createByReal(-tol_gap)
                        for native_face, native_body in cuts_needed:
                            try:
                                col = adsk.core.ObjectCollection.create()
                                col.add(native_face)
                                ext_input = extrudes.createInput(col, adsk.fusion.FeatureOperations.CutFeatureOperation)
                                ext_input.setDistanceExtent(False, dist_input)
                                ext_input.participantBodies = [native_body]
                                f = extrudes.add(ext_input)
                                created_feats.append(f)
                            except: pass
                        if len(created_feats) > 0:
                            try:
                                tl = design.timeline
                                start = created_feats[0].timelineObject.index
                                end = created_feats[-1].timelineObject.index
                                if end >= start:
                                    g = tl.groups.add(start, end)
                                    g.name = "Tolerance Cuts"
                            except: pass

            # --- MOVE TO TARGET ---
            if not new_transform.isEqualTo(identity_transform):
                design.activateRootComponent()
                new_occ.transform = new_transform
                adsk.doEvents()

            # --- PANELS ---
            new_occ.activate()

            def create_cover_panel(is_back):
                p_sketch = sketches.add(new_comp.xYConstructionPlane)
                p0 = adsk.core.Point3D.create(0,0,0)
                p1 = adsk.core.Point3D.create(width, height, 0)
                p_sketch.sketchCurves.sketchLines.addTwoPointRectangle(p0, p1)
                prof = p_sketch.profiles.item(0)
                ext_in = extrudes.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
                
                pth_inch = panel_th / 2.54
                pth_str = f"{pth_inch:.6f} in"
                dep_inch = depth / 2.54
                dep_str = f"{dep_inch:.6f} in"

                if is_back:
                    ext_in.startExtent = adsk.fusion.FromEntityStartDefinition.create(new_comp.xYConstructionPlane, adsk.core.ValueInput.createByReal(0))
                    ext_in.setDistanceExtent(False, adsk.core.ValueInput.createByString(f"-{pth_str}"))
                    nm = "Back Panel"
                else:
                    ext_in.startExtent = adsk.fusion.FromEntityStartDefinition.create(new_comp.xYConstructionPlane, adsk.core.ValueInput.createByString(dep_str))
                    ext_in.setDistanceExtent(False, adsk.core.ValueInput.createByString(pth_str))
                    nm = "Front Panel"
                e = extrudes.add(ext_in)
                e.name = nm

            if has_back: create_cover_panel(True)
            if has_front: create_cover_panel(False)

            # --- APPEARANCE ---
            def get_appear(name_list):
                for name in name_list:
                    if design.appearances.itemByName(name): return design.appearances.itemByName(name)
                for lib in app.materialLibraries:
                    for name in name_list:
                        try:
                            found = lib.appearances.itemByName(name)
                            if found:
                                try: return design.appearances.addByCopy(found, name)
                                except: return design.appearances.itemByName(name)
                        except: continue
                return None

            pine_appear = get_appear(["Pine", "Pine - Natural", "Wood - Pine"])
            white_appear = get_appear(["Paint - Enamel Glossy (White)", "Plastic - Matte (White)", "Opaque - White", "White"])

            for body in new_comp.bRepBodies:
                if "Panel" in body.name:
                    if white_appear: body.appearance = white_appear
                else:
                    if pine_appear: body.appearance = pine_appear

            design.activateRootComponent()

        except:
            if adsk.core.Application.get().userInterface:
                adsk.core.Application.get().userInterface.messageBox('Failed:\n{}'.format(traceback.format_exc()))

    def analyze_tolerance(self, app, target_bodies):
        cuts = []
        try:
            measure_mgr = app.measureManager
            touch_tolerance = 0.005 
            
            def are_faces_parallel(face1, face2):
                try:
                    ret1, param1 = face1.evaluator.getParameterAtPoint(face1.pointOnFace)
                    ret2, normal1 = face1.evaluator.getNormalAtParameter(param1)
                    ret3, param2 = face2.evaluator.getParameterAtPoint(face2.pointOnFace)
                    ret4, normal2 = face2.evaluator.getNormalAtParameter(param2)
                    if not ret2 or not ret4: return False
                    dot = normal1.dotProduct(normal2)
                    return abs(dot) > 0.99
                except: return False

            def is_overlapping(face1, face2):
                try:
                    # Check multiple points for better overlap detection
                    if face2.isPointOnFace(face1.pointOnFace): return True
                    if face1.isPointOnFace(face2.pointOnFace): return True
                    # Also check bounding box overlap as fallback
                    bb1 = face1.boundingBox
                    bb2 = face2.boundingBox
                    if bb1.intersects(bb2):
                        return True
                    return False
                except: return False

            def is_plate_main_surface(body, face, normal):
                """Check if this face is a main top/bottom surface of a Plate (not a finger interface)"""
                if "Plate" not in body.name:
                    return False
                if abs(normal.y) < 0.9:
                    return False  # Not a Y-facing face
                try:
                    body_bb = body.boundingBox
                    face_bb = face.boundingBox
                    face_y = (face_bb.minPoint.y + face_bb.maxPoint.y) / 2
                    # Check if face is at the body's Y extremes (main top or bottom surface)
                    if abs(face_y - body_bb.minPoint.y) < 0.01:
                        return True  # At bottom of plate
                    if abs(face_y - body_bb.maxPoint.y) < 0.01:
                        return True  # At top of plate
                except:
                    pass
                return False

            def is_exterior_z_face(body, face, normal):
                """Check if this Z-facing face is on the exterior (front/back of panel)"""
                if abs(normal.z) < 0.9:
                    return False  # Not a Z-facing face
                try:
                    body_bb = body.boundingBox
                    face_bb = face.boundingBox
                    face_z = (face_bb.minPoint.z + face_bb.maxPoint.z) / 2
                    # Check if face is at the body's Z extremes (exterior front or back)
                    if abs(face_z - body_bb.minPoint.z) < 0.01:
                        return True  # At front of body
                    if abs(face_z - body_bb.maxPoint.z) < 0.01:
                        return True  # At back of body
                except:
                    pass
                return False

            for i, body_A in enumerate(target_bodies):
                other_bodies = [b for b in target_bodies if b != body_A]
                for face_A in body_A.faces:
                    if face_A.geometry.surfaceType != adsk.core.SurfaceTypes.PlaneSurfaceType: continue
                    
                    ret, param = face_A.evaluator.getParameterAtPoint(face_A.pointOnFace)
                    ret, normal = face_A.evaluator.getNormalAtParameter(param)
                    
                    # Skip X-facing faces (body ends) to preserve width
                    if abs(normal.x) > 0.9: continue
                    
                    # Skip exterior Z-facing faces (front/back of panels) to preserve depth
                    # but allow internal Z-facing faces (between fingers, mortise/tenon)
                    if is_exterior_z_face(body_A, face_A, normal): continue
                    
                    # Skip main top/bottom surfaces of Plates to preserve thickness
                    # (but allow finger interface faces which are internal)
                    if is_plate_main_surface(body_A, face_A, normal): continue

                    should_cut = False
                    face_A_bb = face_A.boundingBox
                    for body_B in other_bodies:
                        if not face_A_bb.intersects(body_B.boundingBox): continue
                        try:
                            dist_val = measure_mgr.measureMinimumDistance(face_A, body_B).value
                        except:
                            continue
                        if dist_val > touch_tolerance: continue
                        touching_face_B = None
                        for face_B in body_B.faces:
                            try:
                                if not face_A_bb.intersects(face_B.boundingBox): continue
                                f_dist = measure_mgr.measureMinimumDistance(face_A, face_B)
                                if f_dist.value <= touch_tolerance:
                                    valid = False
                                    if face_B.geometry.surfaceType == adsk.core.SurfaceTypes.PlaneSurfaceType:
                                        if are_faces_parallel(face_A, face_B) and is_overlapping(face_A, face_B):
                                            valid = True
                                    else:
                                        if is_overlapping(face_A, face_B):
                                            valid = True
                                    if valid:
                                        touching_face_B = face_B
                                        break
                            except:
                                continue
                        if touching_face_B:
                            name_A = body_A.name
                            name_B = body_B.name
                            if "Plate" in name_A and "Stile" in name_B: should_cut = True  
                            elif "Stile" in name_A and "Plate" in name_B: should_cut = False 
                            elif "Stile" in name_A and "Rail" in name_B: should_cut = True   
                            elif "Rail" in name_A and "Stile" in name_B: should_cut = False  
                            else:
                                if face_A.area - touching_face_B.area < -0.0001: should_cut = True
                                elif abs(face_A.area - touching_face_B.area) <= 0.0001:
                                    if face_A.entityToken < touching_face_B.entityToken: should_cut = True
                                    
                            if should_cut: break
                    if should_cut:
                        nat_face = face_A.nativeObject if face_A.nativeObject else face_A
                        nat_body = face_A.body.nativeObject if face_A.body.nativeObject else face_A.body
                        cuts.append((nat_face, nat_body))
        except: pass
        return cuts

    def draw_rect_with_info(self, sketch, x1, y1, x2, y2, dim_h=True, dim_v=True):
        lines = sketch.sketchCurves.sketchLines
        p1 = adsk.core.Point3D.create(x1, y1, 0)
        p2 = adsk.core.Point3D.create(x2, y1, 0)
        p3 = adsk.core.Point3D.create(x2, y2, 0)
        p4 = adsk.core.Point3D.create(x1, y2, 0)
        l1 = lines.addByTwoPoints(p1, p2)
        l2 = lines.addByTwoPoints(p2, p3)
        l3 = lines.addByTwoPoints(p3, p4)
        l4 = lines.addByTwoPoints(p4, p1)
        
        gc = sketch.geometricConstraints
        try: gc.addHorizontal(l1); gc.addVertical(l2); gc.addHorizontal(l3); gc.addVertical(l4)
        except: pass
        try: gc.addCoincident(l1.endSketchPoint, l2.startSketchPoint); gc.addCoincident(l2.endSketchPoint, l3.startSketchPoint)
        except: pass
        try: gc.addCoincident(l3.endSketchPoint, l4.startSketchPoint); gc.addCoincident(l4.endSketchPoint, l1.startSketchPoint)
        except: pass
        
        dims = sketch.sketchDimensions
        if dim_h:
            try: 
                dims.addDistanceDimension(l1.startSketchPoint, l1.endSketchPoint, 
                                          adsk.fusion.DimensionOrientations.HorizontalDimensionOrientation, 
                                          adsk.core.Point3D.create((x1+x2)/2, y1-1, 0))
            except: pass
        if dim_v:
            try: 
                dims.addDistanceDimension(l2.startSketchPoint, l2.endSketchPoint, 
                                          adsk.fusion.DimensionOrientations.VerticalDimensionOrientation, 
                                          adsk.core.Point3D.create(x2+1, (y1+y2)/2, 0))
            except: pass
        
        return {'lines': [l1, l2, l3, l4], 'points': [l1.startSketchPoint, l1.endSketchPoint, l2.endSketchPoint, l3.endSketchPoint]}

    def draw_rect(self, lines, x1, y1, x2, y2):
        p1 = adsk.core.Point3D.create(x1, y1, 0)
        p2 = adsk.core.Point3D.create(x2, y1, 0)
        p3 = adsk.core.Point3D.create(x2, y2, 0)
        p4 = adsk.core.Point3D.create(x1, y2, 0)
        l1 = lines.addByTwoPoints(p1, p2)  # bottom line
        l2 = lines.addByTwoPoints(p2, p3)  # right line
        l3 = lines.addByTwoPoints(p3, p4)  # top line
        l4 = lines.addByTwoPoints(p4, p1)  # left line
        return {'lines': [l1, l2, l3, l4], 'points': [l1.startSketchPoint, l1.endSketchPoint, l2.endSketchPoint, l3.endSketchPoint]}

    def draw_sketch_rect_3d(self, sketch, lines, offset_x, y_center, t_height, z_min, z_max):
        y_min = y_center - (t_height / 2.0)
        y_max = y_center + (t_height / 2.0)
        world_p1 = adsk.core.Point3D.create(offset_x, y_min, z_min)
        world_p2 = adsk.core.Point3D.create(offset_x, y_max, z_max)
        sketch_p1 = sketch.modelToSketchSpace(world_p1)
        sketch_p2 = sketch.modelToSketchSpace(world_p2)
        return lines.addTwoPointRectangle(sketch_p1, sketch_p2)