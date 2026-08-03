'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { useModelContext } from '@/context/model-context';
import Image from 'next/image'; // For preview display
import { X } from 'lucide-react'; // Icon for remove button

export function ImageUploader() {
  const { setUploadedFiles, generateModel, isLoading } = useModelContext();
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [previewUrls, setPreviewUrls] = useState<string[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Clean up preview URLs when component unmounts or files change
  useEffect(() => {
    return () => {
      previewUrls.forEach(url => URL.revokeObjectURL(url));
    };
  }, [previewUrls]);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files) {
      const fileList = Array.from(files);
      setSelectedFiles(fileList);
      setUploadedFiles(fileList); // Update context

      // Create preview URLs
      const currentPreviewUrls = fileList.map(file => URL.createObjectURL(file));
      // Clean up previous URLs before setting new ones
      previewUrls.forEach(url => URL.revokeObjectURL(url));
      setPreviewUrls(currentPreviewUrls);
    }
  };

  const handleSelectClick = () => {
    fileInputRef.current?.click(); // Trigger hidden file input
  };

  const handleClearClick = () => {
    setSelectedFiles([]);
    setUploadedFiles([]); // Update context
    // Clean up URLs
    previewUrls.forEach(url => URL.revokeObjectURL(url));
    setPreviewUrls([]);
    // Reset file input value
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };
  
  const handleGenerateClick = () => {
    generateModel(selectedFiles);
  };

  return (
    <Card className="w-full max-w-lg">
      <CardHeader>
        <CardTitle>Upload Dental Scan Images</CardTitle>
        <CardDescription>Select the images needed to generate the 3D model.</CardDescription>
      </CardHeader>
      <CardContent>
        {/* Hidden file input */}
        <Input
          ref={fileInputRef}
          type="file"
          multiple
          accept="image/*" // Accept only images
          onChange={handleFileChange}
          className="hidden"
        />
        
        {/* Previews */}
        {previewUrls.length > 0 ? (
          <div className="grid grid-cols-3 gap-4 mb-4">
            {previewUrls.map((url, index) => (
              <div key={index} className="relative aspect-square border rounded overflow-hidden">
                <Image 
                  src={url} 
                  alt={`Preview ${index + 1}`}
                  layout="fill"
                  objectFit="cover"
                />
              </div>
            ))}
          </div>
        ) : (
          <div className="h-32 border-2 border-dashed rounded-md flex items-center justify-center text-gray-500 mb-4">
            <span>No images selected</span>
          </div>
        )}
        
        {/* Action Buttons */}
        <div className="flex justify-between items-center">
          <Button onClick={handleSelectClick} variant="outline">
            {selectedFiles.length > 0 ? "Change Selection" : "Select Image"}
          </Button>
          {selectedFiles.length > 0 && (
            <Button onClick={handleClearClick} variant="ghost" size="sm">
              <X className="h-4 w-4 mr-1"/> Clear
            </Button>
          )}
        </div>
      </CardContent>
      <CardFooter>
         <Button 
            onClick={handleGenerateClick} 
            disabled={selectedFiles.length === 0 || isLoading}
            className="w-full"
          >
            {isLoading ? "Generating..." : "Generate 3D Model"}
          </Button>
      </CardFooter>
    </Card>
  );
} 