/*
 * To change this license header, choose License Headers in Project Properties.
 * To change this template file, choose Tools | Templates
 * and open the template in the editor.
 */

package xmipp.ij.commons;

/**
 *
 * @author airen
 */
 public class Geometry
        {
            public double shiftx, shifty, psiangle;
            public boolean flip;
            
            private String matrixString;
            
            public Geometry(double shiftx, double shifty, double psiangle, boolean flip)
            {
                this.shiftx = shiftx;
                this.shifty = shifty;
                this.psiangle = psiangle;
                this.flip = flip;
                this.matrixString = null;
            }
            
            public Geometry(String matrixString)
            {
            	this.matrixString = matrixString;
            }
            
            public String getMatrix()
            {
            	return this.matrixString;
            }
            
            public boolean hasMatrix()
            {
            	return this.matrixString != null;
            }
        }

        