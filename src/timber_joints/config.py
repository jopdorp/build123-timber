"""Central configuration for timber joints.

All gap/clearance-related parameters are derived from MORTISE_CLEARANCE,
which is the physical clearance between tenon and mortise surfaces.

This ensures consistency between:
- CAD geometry (mortise cuts)
- Mesh contact detection
- FEA contact analysis
"""

from dataclasses import dataclass


# =============================================================================
# Master Configuration
# =============================================================================

# The physical clearance between tenon and mortise surfaces (mm)
# This is the single source of truth for all related parameters
# 
# Set very small (0.001mm = 1 micron) to minimize artificial strain from
# the CalculiX ADJUST parameter moving nodes to close gaps. A larger gap
# would inject strain energy like a compressed spring.
MORTISE_CLEARANCE: float = 0.2  # mm


@dataclass(frozen=True)
class TimberJointConfig:
    """Central configuration derived from mortise clearance.
    
    All parameters are computed as ratios of the base mortise clearance
    to ensure physical consistency across CAD, meshing, and FEA.
    """
    
    # Base clearance (the physical gap in the joint)
    mortise_clearance: float = MORTISE_CLEARANCE
    
    @property
    def cad_cut_margin(self) -> float:
        """Margin for create_receiving_cut() - makes mortise larger than tenon.
        
        Should equal mortise_clearance for accurate geometry.
        """
        return self.mortise_clearance
    
    @property
    def contact_gap(self) -> float:
        """CalculiX contact gap (c0) - clearance for pressure-overclosure.
        
        Should be slightly larger than mortise_clearance to allow for:
        - Mesh discretization error
        - Initial contact establishment
        
        Ratio: 4x mortise clearance
        """
        return self.mortise_clearance * 4.0
    
    @property
    def contact_adjust(self) -> float:
        """CalculiX ADJUST parameter - moves slave nodes toward master.
        
        Should be larger than contact_gap to ensure contact can establish.
        
        Ratio: 5x mortise clearance  
        """
        return self.mortise_clearance * 5.0
    
    @property
    def mesh_contact_tolerance(self) -> float:
        """Tolerance for mesh contact face detection.
        
        Faces within this distance are considered potential contacts.
        Should be larger than contact_gap to capture all contact faces.
        
        Ratio: 1x mortise clearance (added to element-size-based margin)
        """
        return self.mortise_clearance
    
    def __repr__(self) -> str:
        return (
            f"TimberJointConfig(\n"
            f"  mortise_clearance={self.mortise_clearance} mm (base)\n"
            f"  cad_cut_margin={self.cad_cut_margin} mm\n"
            f"  contact_gap={self.contact_gap} mm\n"
            f"  contact_adjust={self.contact_adjust} mm\n"
            f"  mesh_contact_tolerance={self.mesh_contact_tolerance} mm\n"
            f")"
        )


# Global default configuration instance
DEFAULT_CONFIG = TimberJointConfig()


def get_config(mortise_clearance: float = None) -> TimberJointConfig:
    """Get configuration, optionally with custom mortise clearance.
    
    Args:
        mortise_clearance: Override default clearance (mm)
        
    Returns:
        TimberJointConfig with all derived parameters
    """
    if mortise_clearance is None:
        return DEFAULT_CONFIG
    return TimberJointConfig(mortise_clearance=mortise_clearance)
