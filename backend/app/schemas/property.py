"""
Property schemas for request/response validation.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict


class LocationBase(BaseModel):
    """Base location schema."""
    address: str = Field(..., max_length=500, description="Property address")
    city: str = Field(..., max_length=100, description="City")
    state: str = Field(..., max_length=100, description="State/Province")
    country: str = Field(default="US", max_length=100, description="Country")
    zipcode: Optional[str] = Field(None, max_length=20, description="Postal code")
    latitude: Optional[Decimal] = Field(None, description="Latitude coordinate")
    longitude: Optional[Decimal] = Field(None, description="Longitude coordinate")


class PropertyBase(BaseModel):
    """Base property schema with common fields."""
    title: str = Field(..., max_length=200, description="Property title")
    description: Optional[str] = Field(None, description="Property description")
    property_type: str = Field(..., max_length=100, description="Type of property")
    bedrooms: Optional[int] = Field(None, ge=0, description="Number of bedrooms")
    bathrooms: Optional[Decimal] = Field(None, ge=0, description="Number of bathrooms")
    square_feet: Optional[int] = Field(None, gt=0, description="Square footage")
    lot_size: Optional[Decimal] = Field(None, ge=0, description="Lot size in acres")
    year_built: Optional[int] = Field(None, ge=1800, le=2030, description="Year built")
    list_price: Decimal = Field(..., gt=0, description="Listed price")
    estimated_value: Optional[Decimal] = Field(None, gt=0, description="Estimated market value")
    rental_estimate: Optional[Decimal] = Field(None, ge=0, description="Monthly rental estimate")
    property_taxes: Optional[Decimal] = Field(None, ge=0, description="Annual property taxes")
    hoa_fees: Optional[Decimal] = Field(None, ge=0, description="Monthly HOA fees")
    listing_url: Optional[str] = Field(None, description="Original listing URL")


class PropertyCreate(PropertyBase, LocationBase):
    """Property creation schema."""
    pass


class PropertyRead(PropertyBase, LocationBase):
    """Property read schema for API responses."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID = Field(..., description="Property ID")
    created_at: datetime = Field(..., description="Property creation timestamp")
    updated_at: datetime = Field(..., description="Property last update timestamp")


class PropertyUpdate(BaseModel):
    """Property update schema."""
    title: Optional[str] = Field(None, max_length=200, description="Property title")
    description: Optional[str] = Field(None, description="Property description")
    property_type: Optional[str] = Field(None, max_length=100, description="Type of property")
    bedrooms: Optional[int] = Field(None, ge=0, description="Number of bedrooms")
    bathrooms: Optional[Decimal] = Field(None, ge=0, description="Number of bathrooms")
    square_feet: Optional[int] = Field(None, gt=0, description="Square footage")
    lot_size: Optional[Decimal] = Field(None, ge=0, description="Lot size in acres")
    year_built: Optional[int] = Field(None, ge=1800, le=2030, description="Year built")
    list_price: Optional[Decimal] = Field(None, gt=0, description="Listed price")
    estimated_value: Optional[Decimal] = Field(None, gt=0, description="Estimated market value")
    rental_estimate: Optional[Decimal] = Field(None, ge=0, description="Monthly rental estimate")
    property_taxes: Optional[Decimal] = Field(None, ge=0, description="Annual property taxes")
    hoa_fees: Optional[Decimal] = Field(None, ge=0, description="Monthly HOA fees")
    listing_url: Optional[str] = Field(None, description="Original listing URL")
    # Location fields
    address: Optional[str] = Field(None, max_length=500, description="Property address")
    city: Optional[str] = Field(None, max_length=100, description="City")
    state: Optional[str] = Field(None, max_length=100, description="State/Province")
    country: Optional[str] = Field(None, max_length=100, description="Country")
    zipcode: Optional[str] = Field(None, max_length=20, description="Postal code")
    latitude: Optional[Decimal] = Field(None, description="Latitude coordinate")
    longitude: Optional[Decimal] = Field(None, description="Longitude coordinate")


class PropertyInDB(PropertyBase, LocationBase):
    """Property schema for database operations."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class PropertySummary(BaseModel):
    """Property summary schema for list views."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID = Field(..., description="Property ID")
    title: str = Field(..., description="Property title")
    property_type: str = Field(..., description="Type of property")
    city: str = Field(..., description="City")
    state: str = Field(..., description="State/Province")
    list_price: Decimal = Field(..., description="Listed price")
    estimated_value: Optional[Decimal] = Field(None, description="Estimated market value")
    bedrooms: Optional[int] = Field(None, description="Number of bedrooms")
    bathrooms: Optional[Decimal] = Field(None, description="Number of bathrooms")
    square_feet: Optional[int] = Field(None, description="Square footage")
    created_at: datetime = Field(..., description="Property creation timestamp")


class PropertySearchQuery(BaseModel):
    """Property search query schema."""
    city: Optional[str] = Field(None, description="Filter by city")
    state: Optional[str] = Field(None, description="Filter by state")
    property_type: Optional[str] = Field(None, description="Filter by property type")
    min_price: Optional[Decimal] = Field(None, ge=0, description="Minimum price")
    max_price: Optional[Decimal] = Field(None, gt=0, description="Maximum price")
    min_bedrooms: Optional[int] = Field(None, ge=0, description="Minimum bedrooms")
    max_bedrooms: Optional[int] = Field(None, ge=0, description="Maximum bedrooms")
    min_square_feet: Optional[int] = Field(None, gt=0, description="Minimum square footage")
    max_square_feet: Optional[int] = Field(None, gt=0, description="Maximum square footage")
    skip: int = Field(default=0, ge=0, description="Number of records to skip")
    limit: int = Field(default=10, ge=1, le=100, description="Number of records to return")
