'use client';

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { ParticipationModal } from '@/components/participation-modal';

export default function ParticipatePage() {
  const [modalOpen, setModalOpen] = useState(false);

  return (
    <div className="min-h-screen bg-white text-gray-900 space-y-12 py-12 px-4">
      <section className="text-center py-16 bg-gradient-to-b from-blue-50 to-white rounded-lg shadow-sm">
        <h1 className="text-3xl md:text-4xl font-bold mb-4 text-blue-900">Creating Immersive Learning Experiences with Generative AI</h1>
        <p className="text-md md:text-lg max-w-3xl mx-auto text-gray-700 px-4">
          Empowering Dental Educators to Craft VR Learning Experiences Without Technical Barriers.
        </p>
      </section>

      <section className="px-4 md:px-6 max-w-4xl mx-auto space-y-10">
        <div className="bg-gray-50 p-6 rounded-lg shadow-sm">
          <h2 className="text-xl md:text-2xl font-semibold mb-3 text-blue-800">Introduction</h2>
          <p className="text-gray-700 leading-relaxed">
            Virtual Reality (VR) is transforming dental education through realistic, immersive simulations. However, content creation remains a major hurdle due to technical complexity. Our research proposes AI-powered solutions to democratize 3D content creation for educators.
          </p>
        </div>

        <div className="bg-gray-50 p-6 rounded-lg shadow-sm">
          <h2 className="text-xl md:text-2xl font-semibold mb-3 text-blue-800">Research Questions</h2>
          <ul className="list-disc pl-6 space-y-2 text-gray-700">
            <li>How can AI-aided authoring tools foster pedagogical ownership among dental educators in creating 3D content for Virtual Reality Haptic Dental Simulators (VRHDS)?</li>
            <li>How can we develop 3D algorithms to facilitate the creation of accurate and pedagogically relevant dental models for VRHDS by educators?</li>
            <li>What is the impact of AI-aided authoring tools and specialised 3D dental modelling algorithms on student learning outcomes in VRHDS-based dental education?</li>
          </ul>
        </div>

        <div className="bg-gray-50 p-6 rounded-lg shadow-sm">
          <h2 className="text-xl md:text-2xl font-semibold mb-3 text-blue-800">Methodology</h2>
          <p className="text-gray-700 leading-relaxed">
            We used a mixed-methods approach (surveys and interviews) across UK dental faculties to understand challenges and expectations regarding VR-Haptic simulator content creation.
          </p>
        </div>

        <div className="bg-gray-50 p-6 rounded-lg shadow-sm">
          <h2 className="text-xl md:text-2xl font-semibold mb-3 text-blue-800">Challenges Identified</h2>
          <ul className="list-disc pl-6 space-y-2 text-gray-700">
            <li>Time-consuming 3D content creation</li>
            <li>Steep learning curves of current authoring tools</li>
            <li>Limited open educational resources and platform lock-in</li>
          </ul>
        </div>

        <div className="bg-gray-50 p-6 rounded-lg shadow-sm">
          <h2 className="text-xl md:text-2xl font-semibold mb-3 text-blue-800">Our Solution</h2>
          <ul className="list-disc pl-6 space-y-2 text-gray-700">
            <li>Text-to-3D model generation using enriched prompts</li>
            <li>Image-to-3D conversion for enhanced 3D model realism</li>
            <li>Instructional overlays and voice integration for XR learning</li>
            <li>Easily edit and customise 3D models using text and other simple interactions.</li>
          </ul>
        </div>

        <div className="bg-gray-50 p-6 rounded-lg shadow-sm">
          <h2 className="text-xl md:text-2xl font-semibold mb-3 text-blue-800">Future Work</h2>
          <p className="text-gray-700 leading-relaxed">
            We aim to develop comprehensive evaluation frameworks for AI-generated models, ensuring quality, accuracy, and strong pedagogical alignment while empowering educators to retain full ownership of their instructional designs.
          </p>
        </div>

        <div className="text-center pt-6">
          <Button size="lg" onClick={() => setModalOpen(true)}>Participate in Our Research</Button>
        </div>
      </section>

      <ParticipationModal isOpen={modalOpen} onOpenChange={setModalOpen} />
    </div>
  );
} 