from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

class OpportunityItem(BaseModel):
    """
    Model data standar untuk informasi Lomba maupun Beasiswa
    """
    title: str = Field(..., description="Judul lomba atau beasiswa")
    category: str = Field(..., description="Jenis: 'Lomba' atau 'Beasiswa'")
    tags: List[str] = Field(default_factory=list, description="Kategori spesifik misal: IT, Desain, Business, Full, Partial")
    organizer: str = Field(default="Tidak diketahui", description="Penyelenggara / Institusi")
    description: str = Field(default="", description="Deskripsi singkat atau ringkasan syarat")
    url: str = Field(..., description="Tautan informasi atau pendaftaran")
    deadline: Optional[str] = Field(default=None, description="Tanggal penutupan (YYYY-MM-DD atau teks)")
    source: str = Field(default="Web", description="Asal sumber data (e.g. Puspresnas, Instagram, BeasiswaID)")
    image_url: Optional[str] = Field(default=None, description="Poster atau gambar thumbnail")
    source_id: Optional[str] = Field(default=None, description="ID unik atau slug dari sumber untuk deduplikasi")
