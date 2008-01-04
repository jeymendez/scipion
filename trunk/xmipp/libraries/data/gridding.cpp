/***************************************************************************
 *
 * Authors: Sjors H.W. Scheres (scheres@cnb.uam.es)
 *
 *  This code is strongly based on ideas by Pawel Penczek & Zhengfan
 *  Yang as implemented in SPARX at the University of Texas - Houston 
 *  Medical School
 *
 *  see P. A. Penczek, R. Renka, and H. Schomberg,
 *      J. Opt. Soc. Am. _21_, 449 (2004)
 *
 * Unidad de  Bioinformatica of Centro Nacional de Biotecnologia , CSIC
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA
 * 02111-1307  USA
 *
 *  All comments concerning this program package may be sent to the
 *  e-mail address 'xmipp@cnb.uam.es'
 ***************************************************************************/
#include "gridding.h"

void produceReverseGriddingFourierMatrix2D(const Matrix2D< std::complex< double > > &in, 
					   Matrix2D< std::complex< double > > &out,
					   KaiserBessel &kb)
{
    Matrix2D<double> aux;
    InverseFourierTransform(in,aux);
    aux.setXmippOrigin();
    produceReverseGriddingFourierMatrix2D(aux,out,kb);
}

void produceReverseGriddingFourierMatrix2D(const Matrix2D< double > &in, 
					   Matrix2D< std::complex< double > > &out,
					   KaiserBessel &kb)
{
    // 1. Set up constants and Kaiser-Bessel object
    int Nx = XSIZE(in) * GRIDDING_NPAD;
    int Ny = YSIZE(in) * GRIDDING_NPAD;
    double r = XSIZE(in) / 2.;
    double v = GRIDDING_K / (2. * Nx);
    kb = KaiserBessel(GRIDDING_ALPHA, GRIDDING_K, r, v , Nx);

    // 2. Divide in real space by a sinhwin
    Matrix2D<double> aux2;
    double wx, wy;
    aux2.resize(Ny,Nx);
    aux2.setXmippOrigin();
    FOR_ALL_ELEMENTS_IN_MATRIX2D(in) {
	wy=kb.sinhwin(i);
	wx=kb.sinhwin(j);
	MAT_ELEM(aux2,i,j) = MAT_ELEM(in,i,j) / (wx * wy);
    }
    
    // 3. FFT & (forward) centering
    FourierTransform(aux2,out);
    CenterOriginFFT(out,true);
    
}

// Prepare a 2D real-space image for gridding
void produceReverseGriddingMatrix2D(const Matrix2D< double > &in, 
				    Matrix2D< double > &out,
				    KaiserBessel &kb)
{
    // 1. Set up constants and Kaiser-Bessel object
    int Nx = XSIZE(in) * GRIDDING_NPAD;
    int Ny = YSIZE(in) * GRIDDING_NPAD;
    double r = XSIZE(in) / 2.;
    double v = GRIDDING_K / (2. * Nx);
    kb = KaiserBessel(GRIDDING_ALPHA, GRIDDING_K, r, v , Nx);
    
    // 2. FFT, pad with zeros and divide in Fourier space by a sinhwin
    Matrix2D<std::complex<double> > aux,aux2;
    double wx, wy;
    FourierTransform(in,aux);
    CenterFFT(aux,true);
    aux.setXmippOrigin();
    aux2.resize(Ny,Nx);
    aux2.setXmippOrigin();
    FOR_ALL_ELEMENTS_IN_MATRIX2D(aux) {
	wy=kb.sinhwin(i);
	wx=kb.sinhwin(j);
	MAT_ELEM(aux2,i,j) = MAT_ELEM(aux,i,j) / (wx * wy);
    }
 
    // 3. (backward) centering & IFFT
    CenterFFT(aux2,false);
    InverseFourierTransform(aux2,out);
    out.setXmippOrigin();

}

// Prepare a 3D Fourier-space volume for gridding
void produceReverseGriddingFourierMatrix3D(const Matrix3D< std::complex< double > > &in, 
					   Matrix3D< std::complex< double > > &out,
					   KaiserBessel &kb)
{
    Matrix3D<double> aux;
    InverseFourierTransform(in,aux);
    aux.setXmippOrigin();
    produceReverseGriddingFourierMatrix3D(aux,out,kb);
}

void produceReverseGriddingFourierMatrix3D(const Matrix3D< double > &in, 
					   Matrix3D< std::complex< double > > &out,
					   KaiserBessel &kb)
{
    // 1. Set up constants and Kaiser-Bessel object
    int Nx = XSIZE(in) * GRIDDING_NPAD;
    int Ny = YSIZE(in) * GRIDDING_NPAD;
    int Nz = ZSIZE(in) * GRIDDING_NPAD;
    double r = XSIZE(in) / 2.;
    double v = GRIDDING_K / (2. * Nx);
    kb = KaiserBessel(GRIDDING_ALPHA, GRIDDING_K, r, v , Nx);

    // 2. iFFT, pad with zeros and divide in real space by a sinhwin
    Matrix3D<double> aux2;
    double wx, wy, wz;
    aux2.resize(Nz,Ny,Nx);
    aux2.setXmippOrigin();
    FOR_ALL_ELEMENTS_IN_MATRIX3D(in) {
	wz=kb.sinhwin(k);
	wy=kb.sinhwin(i);
	wx=kb.sinhwin(j);
	VOL_ELEM(aux2,k,i,j) = VOL_ELEM(in,k,i,j) / (wx * wy * wz);
    }
    
    // 3. FFT & (forward) centering
    FourierTransform(aux2,out);
    CenterOriginFFT(out,true);
    
}

// Prepare a 3D real-space volume for gridding
void produceReverseGriddingMatrix3D(const Matrix3D< double > &in, 
				    Matrix3D< double > &out,
				    KaiserBessel &kb)
{
    // 1. Set up constants and Kaiser-Bessel object
    int Nx = XSIZE(in) * GRIDDING_NPAD;
    int Ny = YSIZE(in) * GRIDDING_NPAD;
    int Nz = ZSIZE(in) * GRIDDING_NPAD;
    double r = XSIZE(in) / 2.;
    double v = GRIDDING_K / (2. * Nx);
    kb = KaiserBessel(GRIDDING_ALPHA, GRIDDING_K, r, v , Nx);
    
    // 2. Center FFT and divide in Fourier space by a sinhwin
    Matrix3D<std::complex<double> > aux,aux2;
    double wx, wy, wz;
    FourierTransform(in,aux);
    CenterFFT(aux,true);
    aux.setXmippOrigin();
    aux2.resize(Nz,Ny,Nx);
    aux2.setXmippOrigin();
    FOR_ALL_ELEMENTS_IN_MATRIX3D(aux) {
	wz=kb.sinhwin(k);
	wy=kb.sinhwin(i);
	wx=kb.sinhwin(j);
	VOL_ELEM(aux2,k,i,j) = VOL_ELEM(aux,k,i,j) / (wx * wy * wz);
    }

    // 3. (backward) centering & iFFT
    CenterFFT(aux2,false);
    InverseFourierTransform(aux2,out);
    out.setXmippOrigin();

}

void approximateVoronoiArea(std::vector<double> &voronoi_area,
			    const std::vector<double> &xin, const std::vector<double> &yin, 
			    const double oversample)
{

    double dfine,dfine2,dmin2,r2,dim2;
    double minx,miny,maxx,maxy,fx,fy,dx,dy;
    int imin;
 
    // Initialize voronoi_area vector and find limits of coordinates
    voronoi_area.clear();
    minx = miny = MAXFLOAT;
    maxx = maxy = MINFLOAT;
    for (int i = 0; i < xin.size(); i++)
    {
	voronoi_area.push_back(0.);
	if (xin[i] < minx) minx = xin[i];
	if (xin[i] > maxx) maxx = xin[i];
	if (yin[i] < miny) miny = yin[i];
	if (yin[i] > maxy) maxy = yin[i];
    }

    // Loop over all oversampled points and find nearest sampled input point
    dfine = 1./oversample;
    dfine2 = dfine * dfine;
    minx -= dfine;
    miny -= dfine;
    maxx += dfine;
    maxy += dfine;
    for (fx = minx; fx <= maxx; fx += dfine)
    {
	for (fy = miny; fy <= maxy; fy += dfine)
	{
	    dmin2 = MAXFLOAT;
	    for (int i = 0; i < xin.size(); i++)
	    {
		dx = xin[i] - fx;
		dy = yin[i] - fy;
		r2 = dx*dx + dy*dy;
		if ( r2 < dmin2 )
		{
		    dmin2 = r2;
		    imin = i;
		}
	    }
	    voronoi_area[imin] += dfine2;
	}
    }

}

void produceForwardGriddingMatrix2D(const Matrix2D< double > &in, 
				    Matrix2D< double > &out,
				    KaiserBessel &kb)
{

    Matrix2D<std::complex<double> > aux, aux2;
    int xdim,ydim;
    double wx, wy;

    // Downsample result GRIDDING_NPAD times
    xdim = XSIZE(in)/GRIDDING_NPAD; 
    ydim = YSIZE(in)/GRIDDING_NPAD; 

    // FFT and divide in Fourier space by the corresponding sinhwin
    FourierTransform(in,aux);
    CenterFFT(aux,true);
    aux.setXmippOrigin();
    FOR_ALL_ELEMENTS_IN_MATRIX2D(aux) {
	wy=kb.sinhwin(i);
	wx=kb.sinhwin(j);
	MAT_ELEM(aux,i,j) = MAT_ELEM(aux,i,j) / (wx * wy);
    }
 
    // Resize to single dim, (backward) centering and IFFT
    aux2.resize(xdim,ydim);
    aux2.setXmippOrigin();
    FOR_ALL_ELEMENTS_IN_MATRIX2D(aux2)
    {
	MAT_ELEM(aux2,i,j) = MAT_ELEM(aux,i,j);
    }
    CenterFFT(aux2,false);
    InverseFourierTransform(aux2,out);
    out.setXmippOrigin();

}

void produceForwardGriddingMatrix2D(const Matrix2D< std::complex<double > > &in, 
				    Matrix2D< double > &out,
				    KaiserBessel &kb, bool is_centered)
{
    Matrix2D<double> aux;
    int xdim, ydim;
    double wx, wy;

    // Downsample result GRIDDING_NPAD times
    xdim = XSIZE(in)/GRIDDING_NPAD; 
    ydim = YSIZE(in)/GRIDDING_NPAD; 
    out.resize(xdim,ydim);
    out.setXmippOrigin();

    // IFFT and divide in real space by the corresponding sinhwin
    if (is_centered)
    {
	CenterFFT(aux,false);
    }
    InverseFourierTransform(in,aux);
    aux.setXmippOrigin();
    FOR_ALL_ELEMENTS_IN_MATRIX2D(out) {
	wy=kb.sinhwin(i);
	wx=kb.sinhwin(j);
	MAT_ELEM(out,i,j) = MAT_ELEM(aux,i,j) / (wx * wy);
    }

}

void produceForwardGriddingFourierMatrix2D(const Matrix2D< std::complex<double > > &in, 
					   Matrix2D< std::complex<double > > &out,
					   KaiserBessel &kb, bool is_centered)
{
    Matrix2D<double> aux;

    produceForwardGriddingMatrix2D(in,aux,kb,is_centered);
    FourierTransform(aux,out);
    CenterFFT(out,true);

}
