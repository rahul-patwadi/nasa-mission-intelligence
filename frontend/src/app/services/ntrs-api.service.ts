import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../environments/environment';
import { MissionsResponse, QueryRequest, QueryResponse } from '../models/ntrs-api.models';

@Injectable({ providedIn: 'root' })
export class NtrsApiService {
  private readonly baseUrl = environment.apiBaseUrl;

  constructor(private readonly http: HttpClient) {}

  getMissions(): Observable<MissionsResponse> {
    return this.http.get<MissionsResponse>(`${this.baseUrl}/missions`);
  }

  query(request: QueryRequest): Observable<QueryResponse> {
    return this.http.post<QueryResponse>(`${this.baseUrl}/query`, request);
  }
}
